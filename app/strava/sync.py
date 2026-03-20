from datetime import datetime, timezone
from ..models import db, Activity

def parse_dt(s):
    if not s:
        return None
    for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S%z'):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo:
                dt = dt.replace(tzinfo=None)
            return dt
        except ValueError:
            continue
    return None


def save_activity(user, strava_data, client=None):
    """
    Salva ou atualiza uma atividade no banco.
    Retorna a Activity salva ou None se já existia.
    """
    sid = strava_data.get('id')
    if not sid:
        return None

    existing = Activity.query.filter_by(strava_id=sid).first()
    if existing:
        return None  # já sincronizado

    a = Activity(
        user_id          = user.id,
        strava_id        = sid,
        name             = strava_data.get('name'),
        sport_type       = strava_data.get('sport_type') or strava_data.get('type'),
        start_date       = parse_dt(strava_data.get('start_date')),
        start_date_local = parse_dt(strava_data.get('start_date_local')),
        timezone         = strava_data.get('timezone'),
        distance         = strava_data.get('distance', 0),
        moving_time      = strava_data.get('moving_time', 0),
        elapsed_time     = strava_data.get('elapsed_time', 0),
        average_speed    = strava_data.get('average_speed'),
        max_speed        = strava_data.get('max_speed'),
        total_elevation_gain = strava_data.get('total_elevation_gain'),
        elev_high        = strava_data.get('elev_high'),
        elev_low         = strava_data.get('elev_low'),
        average_heartrate= strava_data.get('average_heartrate'),
        max_heartrate    = strava_data.get('max_heartrate'),
        average_cadence  = strava_data.get('average_cadence'),
        calories         = strava_data.get('calories'),
        suffer_score     = strava_data.get('suffer_score'),
        map_polyline     = (strava_data.get('map') or {}).get('polyline'),
        map_summary_polyline = (strava_data.get('map') or {}).get('summary_polyline'),
        splits_metric    = strava_data.get('splits_metric'),
        laps             = strava_data.get('laps'),
    )

    # Buscar streams detalhados se o client estiver disponível
    if client:
        try:
            raw_streams = client.get_activity_streams(sid)
            a.streams = {
                'time':      _stream_data(raw_streams, 'time'),
                'altitude':  _stream_data(raw_streams, 'altitude'),
                'heartrate': _stream_data(raw_streams, 'heartrate'),
                'cadence':   _stream_data(raw_streams, 'cadence'),
                'velocity':  _stream_data(raw_streams, 'velocity_smooth'),
                'latlng':    _stream_data(raw_streams, 'latlng'),
                'moving':    _stream_data(raw_streams, 'moving'),
            }
        except Exception:
            pass  # streams são opcionais — não bloquear o sync

    db.session.add(a)
    db.session.commit()
    return a


def _stream_data(streams_dict, key):
    """Extrai dados de um stream pelo tipo."""
    stream = streams_dict.get(key)
    if stream:
        return stream.get('data')
    return None
