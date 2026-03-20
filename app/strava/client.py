import time
import requests
from flask import current_app
from ..models import db, StravaToken

class StravaClient:
    """Wrapper da Strava API com renovação automática de tokens."""

    BASE = 'https://www.strava.com/api/v3'

    def __init__(self, user):
        self.user  = user
        self.token = user.strava_token

    def _ensure_token(self):
        """Renova o access_token se expirado."""
        if not self.token or not self.token.refresh_token:
            raise ValueError("Usuário não conectou o Strava.")

        if self.token.is_expired():
            resp = requests.post('https://www.strava.com/oauth/token', data={
                'client_id':     current_app.config['STRAVA_CLIENT_ID'],
                'client_secret': current_app.config['STRAVA_CLIENT_SECRET'],
                'grant_type':    'refresh_token',
                'refresh_token': self.token.refresh_token,
            }, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            self.token.access_token  = data['access_token']
            self.token.refresh_token = data['refresh_token']
            self.token.expires_at    = data['expires_at']
            db.session.commit()

    def _get(self, endpoint, params=None):
        self._ensure_token()
        url = f"{self.BASE}{endpoint}"
        resp = requests.get(url, headers={
            'Authorization': f"Bearer {self.token.access_token}"
        }, params=params or {}, timeout=15)

        if resp.status_code == 429:
            raise RuntimeError("Rate limit do Strava atingido. Tente novamente em 15 minutos.")
        if resp.status_code == 401:
            raise ValueError("Token inválido. Reconecte o Strava.")

        resp.raise_for_status()
        return resp.json()

    # ── Athlete ──
    def get_athlete(self):
        return self._get('/athlete')

    def get_athlete_stats(self, strava_athlete_id):
        return self._get(f'/athletes/{strava_athlete_id}/stats')

    def get_athlete_zones(self):
        return self._get('/athlete/zones')

    # ── Activities ──
    def get_activities(self, page=1, per_page=30, after=None, before=None):
        params = {'page': page, 'per_page': per_page}
        if after:  params['after']  = after
        if before: params['before'] = before
        return self._get('/athlete/activities', params)

    def get_activity(self, activity_id):
        return self._get(f'/activities/{activity_id}')

    def get_activity_streams(self, activity_id):
        keys = 'time,distance,altitude,heartrate,cadence,velocity_smooth,latlng,moving'
        return self._get(f'/activities/{activity_id}/streams', {
            'keys': keys,
            'key_by_type': 'true',
            'resolution': 'medium',
        })

    def get_activity_laps(self, activity_id):
        return self._get(f'/activities/{activity_id}/laps')

    # ── Sync completo ──
    def sync_all_activities(self, max_pages=10):
        """Sincroniza todas as atividades do tipo corrida."""
        from .sync import save_activity
        synced = 0
        for page in range(1, max_pages + 1):
            acts = self.get_activities(page=page, per_page=50)
            if not acts:
                break
            for a in acts:
                if a.get('sport_type') in ('Run', 'TrailRun', 'Walk', 'Hike'):
                    saved = save_activity(self.user, a, self)
                    if saved:
                        synced += 1
        return synced

    def sync_new_activities(self, after_timestamp):
        """Sincroniza apenas atividades novas (para webhook)."""
        from .sync import save_activity
        acts = self.get_activities(after=after_timestamp, per_page=30)
        synced = 0
        for a in acts:
            if a.get('sport_type') in ('Run', 'TrailRun', 'Walk', 'Hike'):
                saved = save_activity(self.user, a, self)
                if saved:
                    synced += 1
        return synced
