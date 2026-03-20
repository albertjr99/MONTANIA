from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from datetime import datetime, timedelta, timezone
import pytz

TZ_BRASILIA = pytz.timezone('America/Sao_Paulo')

def now_br():
    """Retorna datetime atual no fuso de Brasília."""
    return datetime.now(TZ_BRASILIA).replace(tzinfo=None)
from ..models import db, Activity, User

api_bp = Blueprint('api', __name__)

def _get_target_user(user_id=None):
    """Resolve qual usuário buscar. Managers/owners podem ver qualquer um."""
    if user_id and current_user.is_manager:
        user = User.query.get_or_404(user_id)
        return user
    return current_user

def _period_filter(query, user_id, period):
    now = now_br()
    if period == 'week':
        start = now - timedelta(days=7)
    elif period == 'month':
        start = now.replace(day=1)
    elif period == 'year':
        start = now.replace(month=1, day=1)
    else:
        start = now - timedelta(days=30)
    return query.filter(
        Activity.user_id == user_id,
        Activity.start_date_local >= start
    )


# ─── Stats cards ───

@api_bp.route('/stats')
@login_required
def stats():
    user_id = request.args.get('user_id', type=int)
    user    = _get_target_user(user_id)
    period  = request.args.get('period', 'month')

    q = _period_filter(Activity.query, user.id, period)
    acts = q.filter(Activity.sport_type.in_(['Run','TrailRun','Walk','Hike'])).all()

    total_km    = sum(a.distance_km for a in acts)
    total_time  = sum(a.moving_time or 0 for a in acts)
    total_cal   = sum(a.calories or 0 for a in acts)
    total_elev  = sum(a.total_elevation_gain or 0 for a in acts)
    count       = len(acts)

    paces = [a.pace_min_km for a in acts if a.pace_min_km]
    avg_pace_secs = sum(paces) / len(paces) if paces else None

    def fmt_time(secs):
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        return f"{h}h {m:02d}m" if h else f"{m}m"

    def fmt_pace(secs):
        if not secs: return '—'
        m = int(secs // 60); s = int(secs % 60)
        return f"{m}'{s:02d}\""

    return jsonify({
        'km':        round(total_km, 1),
        'time':      fmt_time(total_time),
        'pace':      fmt_pace(avg_pace_secs),
        'calories':  int(total_cal),
        'elevation': int(total_elev),
        'count':     count,
    })


# ─── Volume semanal ───

@api_bp.route('/volume-weekly')
@login_required
def volume_weekly():
    user_id = request.args.get('user_id', type=int)
    user    = _get_target_user(user_id)

    weeks_back = 12
    now   = now_br()
    start = now - timedelta(weeks=weeks_back)

    acts = Activity.query.filter(
        Activity.user_id == user.id,
        Activity.sport_type.in_(['Run','TrailRun','Walk','Hike']),
        Activity.start_date_local >= start
    ).all()

    # Agrupar por semana ISO
    weekly = {}
    for a in acts:
        if not a.start_date_local: continue
        iso = a.start_date_local.isocalendar()
        key = f"{iso[0]}-W{iso[1]:02d}"
        weekly[key] = weekly.get(key, 0) + a.distance_km

    # Gerar todas as semanas (mesmo as vazias)
    labels, data = [], []
    for i in range(weeks_back, 0, -1):
        d = now - timedelta(weeks=i)
        iso = d.isocalendar()
        key = f"{iso[0]}-W{iso[1]:02d}"
        labels.append(d.strftime('%-d/%m'))
        data.append(round(weekly.get(key, 0), 1))

    return jsonify({'labels': labels, 'data': data})


# ─── Evolução de pace ───

@api_bp.route('/pace-trend')
@login_required
def pace_trend():
    user_id = request.args.get('user_id', type=int)
    user    = _get_target_user(user_id)

    acts = Activity.query.filter(
        Activity.user_id == user.id,
        Activity.sport_type.in_(['Run','TrailRun']),
        Activity.average_speed > 0,
        Activity.distance >= 3000,   # mínimo 3km
    ).order_by(Activity.start_date_local.asc()).limit(30).all()

    labels = [a.start_date_local.strftime('%-d/%m') if a.start_date_local else '' for a in acts]
    data   = [round(a.pace_min_km / 60, 3) if a.pace_min_km else None for a in acts]

    return jsonify({'labels': labels, 'data': data})


# ─── Fadiga (suffer score) ───

@api_bp.route('/fatigue')
@login_required
def fatigue():
    user_id = request.args.get('user_id', type=int)
    user    = _get_target_user(user_id)

    start = now_br() - timedelta(days=28)
    acts  = Activity.query.filter(
        Activity.user_id == user.id,
        Activity.start_date_local >= start
    ).order_by(Activity.start_date_local.asc()).all()

    # Um ponto por dia
    day_map = {}
    for a in acts:
        if a.start_date_local:
            key = a.start_date_local.strftime('%d/%m')
            day_map[key] = day_map.get(key, 0) + (a.suffer_score or 0)

    labels, data, colors = [], [], []
    for i in range(28):
        d = now_br() - timedelta(days=27-i)
        key = d.strftime('%d/%m')
        val = day_map.get(key, 0)
        labels.append(key)
        data.append(val)
        colors.append('#F87171' if val > 60 else 'rgba(139,92,246,0.6)' if val > 0 else 'rgba(139,92,246,0.1)')

    return jsonify({'labels': labels, 'data': data, 'colors': colors})


# ─── Atividades recentes ───

@api_bp.route('/activities')
@login_required
def activities():
    user_id = request.args.get('user_id', type=int)
    user    = _get_target_user(user_id)
    page    = request.args.get('page', 1, type=int)
    limit   = request.args.get('limit', 20, type=int)

    acts = Activity.query.filter_by(user_id=user.id)\
        .order_by(Activity.start_date_local.desc())\
        .paginate(page=page, per_page=limit, error_out=False)

    return jsonify({
        'activities': [a.to_dict() for a in acts.items],
        'total':   acts.total,
        'pages':   acts.pages,
        'page':    acts.page,
    })


# ─── Detalhe de uma atividade ───

@api_bp.route('/activities/<int:activity_id>')
@login_required
def activity_detail(activity_id):
    a = Activity.query.get_or_404(activity_id)
    if a.user_id != current_user.id and not current_user.is_manager:
        abort(403)
    return jsonify(a.to_dict())


# ─── Grupo (managers/owner) ───

@api_bp.route('/group/stats')
@login_required
def group_stats():
    if not current_user.is_manager:
        abort(403)

    period = request.args.get('period', 'week')
    now    = now_br()
    start  = now - timedelta(days=7 if period == 'week' else 30)

    athletes = User.query.filter_by(role='athlete', active=True).all()
    result   = []

    for ath in athletes:
        acts = Activity.query.filter(
            Activity.user_id == ath.id,
            Activity.start_date_local >= start
        ).all()

        km   = round(sum(a.distance_km for a in acts), 1)
        runs = len(acts)
        paces = [a.pace_min_km for a in acts if a.pace_min_km]
        avg_pace = sum(paces)/len(paces) if paces else None

        def fmt_pace(s):
            if not s: return '—'
            m = int(s//60); sec = int(s%60)
            return f"{m}'{sec:02d}\""

        result.append({
            'id':        ath.id,
            'name':      ath.name,
            'initials':  ''.join(p[0].upper() for p in ath.name.split()[:2]),
            'km':        km,
            'runs':      runs,
            'avg_pace':  fmt_pace(avg_pace),
            'connected': ath.strava_connected,
        })

    result.sort(key=lambda x: x['km'], reverse=True)
    return jsonify({'athletes': result, 'period': period})
