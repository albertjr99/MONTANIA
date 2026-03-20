from flask import Blueprint, redirect, url_for, request, flash, current_app, jsonify
from flask_login import login_required, current_user
import requests, time
from ..models import db, StravaToken, User, Activity
from .client import StravaClient
from .sync import save_activity

strava_bp = Blueprint('strava', __name__)


@strava_bp.route('/connect')
@login_required
def connect():
    """Inicia o fluxo OAuth — redireciona para o Strava."""
    client_id    = current_app.config['STRAVA_CLIENT_ID']
    base_url     = current_app.config['APP_BASE_URL']
    scope        = current_app.config['STRAVA_SCOPE']
    callback_url = f"{base_url}/strava/callback"

    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={callback_url}"
        f"&approval_prompt=force"
        f"&scope={scope}"
    )
    return redirect(auth_url)


@strava_bp.route('/callback')
@login_required
def callback():
    """Recebe o code do Strava e troca por tokens."""
    error = request.args.get('error')
    if error:
        flash('Autorização cancelada.', 'warning')
        return redirect(url_for('dashboard.home'))

    code  = request.args.get('code')
    scope = request.args.get('scope', '')

    if not code:
        flash('Código de autorização não recebido.', 'danger')
        return redirect(url_for('dashboard.home'))

    # Trocar code por tokens
    resp = requests.post('https://www.strava.com/oauth/token', data={
        'client_id':     current_app.config['STRAVA_CLIENT_ID'],
        'client_secret': current_app.config['STRAVA_CLIENT_SECRET'],
        'code':          code,
        'grant_type':    'authorization_code',
    }, timeout=10)

    if resp.status_code != 200:
        flash('Erro ao autenticar com o Strava. Tente novamente.', 'danger')
        return redirect(url_for('dashboard.home'))

    data    = resp.json()
    athlete = data.get('athlete', {})

    # Salvar/atualizar token
    token = current_user.strava_token or StravaToken(user_id=current_user.id)
    token.strava_athlete_id = athlete.get('id')
    token.access_token      = data['access_token']
    token.refresh_token     = data['refresh_token']
    token.expires_at        = data['expires_at']
    token.scope             = scope

    if not current_user.strava_token:
        db.session.add(token)
    db.session.commit()

    flash('Strava conectado com sucesso! Sincronizando atividades...', 'success')

    # Sync inicial — sem streams (rápido, evita timeout do Gunicorn)
    try:
        client = StravaClient(current_user)
        synced = client.sync_all_activities_fast(max_pages=5)
        flash(f'{synced} atividade(s) sincronizada(s)!', 'success')
    except Exception as e:
        flash(f'Strava conectado, mas houve um erro na sincronização: {e}', 'warning')

    return redirect(url_for('dashboard.home'))


@strava_bp.route('/disconnect', methods=['POST'])
@login_required
def disconnect():
    """Remove a conexão com o Strava."""
    if current_user.strava_token:
        db.session.delete(current_user.strava_token)
        db.session.commit()
        flash('Strava desconectado.', 'info')
    return redirect(url_for('dashboard.settings'))


@strava_bp.route('/sync')
@login_required
def sync():
    """Sincronização manual."""
    if not current_user.strava_connected:
        flash('Conecte o Strava primeiro.', 'warning')
        return redirect(url_for('dashboard.home'))

    try:
        client = StravaClient(current_user)
        synced = client.sync_all_activities(max_pages=10)
        flash(f'Sincronização concluída! {synced} nova(s) atividade(s).', 'success')
    except Exception as e:
        flash(f'Erro na sincronização: {e}', 'danger')

    return redirect(url_for('dashboard.home'))


# ─── WEBHOOK ───

@strava_bp.route('/webhook', methods=['GET'])
def webhook_verify():
    """Verificação do webhook pelo Strava (GET)."""
    hub_mode      = request.args.get('hub.mode')
    hub_challenge = request.args.get('hub.challenge')
    hub_verify    = request.args.get('hub.verify_token')

    if hub_mode == 'subscribe' and hub_verify == current_app.config['STRAVA_VERIFY_TOKEN']:
        return jsonify({'hub.challenge': hub_challenge})

    return jsonify({'error': 'Invalid verify token'}), 403


@strava_bp.route('/webhook', methods=['POST'])
def webhook_event():
    """Recebe eventos do Strava (novas atividades, etc)."""
    data = request.get_json(silent=True) or {}

    object_type = data.get('object_type')  # 'activity' ou 'athlete'
    aspect_type = data.get('aspect_type')  # 'create', 'update', 'delete'
    owner_id    = data.get('owner_id')     # strava_athlete_id
    object_id   = data.get('object_id')    # strava_activity_id

    if object_type == 'activity' and aspect_type == 'create' and owner_id:
        # Encontrar o usuário pelo strava_athlete_id
        token = StravaToken.query.filter_by(strava_athlete_id=owner_id).first()
        if token:
            try:
                client = StravaClient(token.user)
                act_data = client.get_activity(object_id)
                if act_data.get('sport_type') in ('Run', 'TrailRun', 'Walk', 'Hike'):
                    save_activity(token.user, act_data, client)
            except Exception:
                pass  # não retornar erro — Strava retentaria

    if object_type == 'athlete' and aspect_type == 'delete':
        # Atleta revogou acesso
        token = StravaToken.query.filter_by(strava_athlete_id=owner_id).first()
        if token:
            db.session.delete(token)
            db.session.commit()

    return jsonify({'status': 'ok'})
