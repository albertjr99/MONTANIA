from flask import Blueprint, request, send_file, abort, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import io, pytz

from ..models import db, Activity, User
from .generator import generate_report

reports_bp = Blueprint('reports', __name__)
TZ_BR = pytz.timezone('America/Sao_Paulo')


def _now():
    return datetime.now(TZ_BR).replace(tzinfo=None)


def _parse_filters(args):
    """Extrai e valida todos os filtros da querystring."""
    period      = args.get('period', 'month')
    sport_type  = args.get('sport_type', '')       # Run, TrailRun, Walk, etc.
    athlete_ids = args.getlist('athlete_id', type=int)
    date_from   = args.get('date_from', '')        # YYYY-MM-DD
    date_to     = args.get('date_to', '')
    min_km      = args.get('min_km', 0, type=float)
    max_km      = args.get('max_km', 9999, type=float)

    now = _now()

    # Resolver data de início
    if date_from:
        try:
            start = datetime.strptime(date_from, '%Y-%m-%d')
        except Exception:
            start = now - timedelta(days=30)
    elif period == 'week':
        start = now - timedelta(days=7)
    elif period == 'month':
        start = now.replace(day=1)
    elif period == '3m':
        start = now - timedelta(days=90)
    elif period == '6m':
        start = now - timedelta(days=180)
    elif period == 'year':
        start = now.replace(month=1, day=1)
    elif period == 'all':
        start = datetime(2000, 1, 1)
    else:
        start = now - timedelta(days=30)

    end = datetime.strptime(date_to, '%Y-%m-%d') if date_to else now

    # Labels legíveis
    PERIOD_LABELS = {
        'week': 'Esta semana', 'month': 'Este mês',
        '3m': 'Últimos 3 meses', '6m': 'Últimos 6 meses',
        'year': 'Este ano', 'all': 'Todo o histórico',
    }
    period_label = PERIOD_LABELS.get(period, period)
    if date_from:
        period_label = f"{date_from} a {date_to or _now().strftime('%Y-%m-%d')}"

    return {
        'start': start, 'end': end,
        'period': period, 'period_label': period_label,
        'sport_type': sport_type,
        'athlete_ids': athlete_ids,
        'min_km': min_km, 'max_km': max_km,
    }


def _build_activity_query(user_id, filters, extra_filters=None):
    """Constrói query de atividades com todos os filtros aplicados."""
    q = Activity.query.filter(
        Activity.user_id == user_id,
        Activity.start_date_local >= filters['start'],
        Activity.start_date_local <= filters['end'],
    )
    if filters['sport_type']:
        q = q.filter(Activity.sport_type == filters['sport_type'])
    else:
        q = q.filter(Activity.sport_type.in_(['Run', 'TrailRun', 'Walk', 'Hike']))
    if extra_filters:
        q = q.filter(*extra_filters)
    return q


@reports_bp.route('/generate')
@login_required
def generate():
    """Gera e faz download do PDF do relatório."""
    if not current_user.is_manager:
        abort(403)

    filters = _parse_filters(request.args)

    # Atletas a incluir
    if filters['athlete_ids']:
        athletes = User.query.filter(
            User.id.in_(filters['athlete_ids']),
            User.role == 'athlete'
        ).all()
    else:
        athletes = User.query.filter_by(role='athlete', active=True).all()

    # Montar dados de cada atleta
    athletes_data = []
    all_acts = []

    for ath in athletes:
        acts = _build_activity_query(ath.id, filters).all()
        if not acts and filters.get('period') != 'all':
            # Incluir mesmo sem atividades para mostrar ausência
            athletes_data.append({
                'name': ath.name, 'km': 0, 'runs': 0,
                'avg_pace': '—', 'elevation': 0, 'calories': 0,
                'avg_hr': None, 'connected': ath.strava_connected,
                'avg_pace_secs': 0, 'streak': 0,
            })
            continue

        km    = round(sum(a.distance_km for a in acts), 1)
        runs  = len(acts)
        elev  = sum(a.total_elevation_gain or 0 for a in acts)
        cal   = sum(a.calories or 0 for a in acts)
        hrs   = [a.average_heartrate for a in acts if a.average_heartrate]
        paces = [a.pace_min_km for a in acts if a.pace_min_km]
        avg_pace_secs = sum(paces)/len(paces) if paces else None

        def fmt_pace(s):
            if not s: return '—'
            m = int(s//60); sc = int(s%60)
            return f"{m}'{sc:02d}\""

        athletes_data.append({
            'name':          ath.name,
            'km':            km,
            'runs':          runs,
            'avg_pace':      fmt_pace(avg_pace_secs),
            'avg_pace_secs': avg_pace_secs or 0,
            'elevation':     int(elev),
            'calories':      int(cal),
            'avg_hr':        round(sum(hrs)/len(hrs), 1) if hrs else None,
            'connected':     ath.strava_connected,
            'streak':        0,
        })
        all_acts.extend(acts)

    # Filtro de km mínimo/máximo
    athletes_data = [
        a for a in athletes_data
        if filters['min_km'] <= a['km'] <= filters['max_km']
    ]

    # Ordenar por km
    athletes_data.sort(key=lambda a: a['km'], reverse=True)

    # Stats do grupo
    trained = [a for a in athletes_data if a['runs'] > 0]
    all_kms   = [a['km'] for a in athletes_data]
    all_paces = [a['avg_pace_secs'] for a in athletes_data if a['avg_pace_secs'] > 0]

    def fmt_pace(s):
        if not s: return '—'
        m = int(s//60); sc = int(s%60)
        return f"{m}'{sc:02d}\""

    group_stats = {
        'total_athletes':  len(athletes_data),
        'athletes_trained': len(trained),
        'total_km':        round(sum(all_kms), 1),
        'total_runs':      sum(a['runs'] for a in athletes_data),
        'total_elevation': int(sum(a['elevation'] for a in athletes_data)),
        'total_calories':  int(sum(a['calories'] for a in athletes_data)),
        'avg_pace_secs':   sum(all_paces)/len(all_paces) if all_paces else None,
        'avg_pace':        fmt_pace(sum(all_paces)/len(all_paces) if all_paces else None),
        'best_athlete':    athletes_data[0]['name'] if athletes_data else '—',
        'min_km':          min(all_kms) if all_kms else 0,
    }

    # Volume semanal do grupo
    weekly = {}
    for act in all_acts:
        if not act.start_date_local: continue
        iso = act.start_date_local.isocalendar()
        key = act.start_date_local.strftime('%-d/%m')
        weekly[key] = weekly.get(key, 0) + act.distance_km

    vol_labels = list(weekly.keys())[-12:]
    vol_data   = [round(weekly[k], 1) for k in vol_labels]

    # Pace médio por semana
    pace_by_week = {}
    for act in all_acts:
        if not act.start_date_local or not act.pace_min_km: continue
        key = act.start_date_local.strftime('%-d/%m')
        if key not in pace_by_week:
            pace_by_week[key] = []
        pace_by_week[key].append(act.pace_min_km)

    pace_labels = list(pace_by_week.keys())[-12:]
    pace_vals   = [round(sum(pace_by_week[k])/len(pace_by_week[k])/60, 3)
                   for k in pace_labels]

    # Filtros para o relatório
    athlete_label = ', '.join(a['name'].split()[0] for a in athletes_data[:4])
    if len(athletes_data) > 4:
        athlete_label += f' +{len(athletes_data)-4}'
    if not athlete_label:
        athlete_label = 'Nenhuma atleta'

    report_filters = {
        'period_label':  filters['period_label'],
        'athlete_label': athlete_label,
        'manager_name':  current_user.name,
        'sport_type':    filters['sport_type'] or 'Todos',
    }

    # Logo
    logo_b64 = current_app.config.get('LOGO_B64_STR', '')

    # Gerar PDF
    pdf_bytes = generate_report(
        athletes_data  = athletes_data,
        group_stats    = group_stats,
        volume_data    = {'labels': vol_labels, 'data': vol_data},
        pace_data      = {'labels': pace_labels, 'data': pace_vals},
        filters        = report_filters,
        logo_b64       = logo_b64,
    )

    now_str = _now().strftime('%Y%m%d_%H%M')
    filename = f'montania_relatorio_{now_str}.pdf'

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )
