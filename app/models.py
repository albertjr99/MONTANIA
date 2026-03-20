from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(180), unique=True, nullable=False)
    password_h = db.Column(db.String(256), nullable=False)
    role       = db.Column(db.String(20), nullable=False, default='athlete')
    # roles: 'owner' | 'manager' | 'athlete'
    active     = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    strava_token = db.relationship('StravaToken', backref='user', uselist=False, cascade='all, delete-orphan')
    activities   = db.relationship('Activity',    backref='user', lazy='dynamic',  cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_h = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_h, password)

    @property
    def is_owner(self):   return self.role == 'owner'
    @property
    def is_manager(self): return self.role in ('owner', 'manager')
    @property
    def strava_connected(self):
        return self.strava_token is not None and self.strava_token.access_token is not None

    def __repr__(self):
        return f'<User {self.email} [{self.role}]>'


class StravaToken(db.Model):
    __tablename__ = 'strava_tokens'

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    strava_athlete_id= db.Column(db.BigInteger)
    access_token     = db.Column(db.String(256))
    refresh_token    = db.Column(db.String(256))
    expires_at       = db.Column(db.Integer)   # Unix timestamp
    scope            = db.Column(db.String(200))
    updated_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def is_expired(self):
        import time
        return self.expires_at is None or time.time() > (self.expires_at - 300)  # 5min buffer

    def __repr__(self):
        return f'<StravaToken user={self.user_id} athlete={self.strava_athlete_id}>'


class Activity(db.Model):
    __tablename__ = 'activities'

    id                   = db.Column(db.Integer, primary_key=True)
    user_id              = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    strava_id            = db.Column(db.BigInteger, unique=True, nullable=False)

    name                 = db.Column(db.String(200))
    sport_type           = db.Column(db.String(60))   # Run, TrailRun, etc.
    start_date           = db.Column(db.DateTime)
    start_date_local     = db.Column(db.DateTime)
    timezone             = db.Column(db.String(80))

    # Distância e tempo
    distance             = db.Column(db.Float)   # metros
    moving_time          = db.Column(db.Integer) # segundos
    elapsed_time         = db.Column(db.Integer) # segundos

    # Velocidade / pace
    average_speed        = db.Column(db.Float)   # m/s
    max_speed            = db.Column(db.Float)   # m/s

    # Elevação
    total_elevation_gain = db.Column(db.Float)   # metros
    elev_high            = db.Column(db.Float)
    elev_low             = db.Column(db.Float)

    # Fisiológico
    average_heartrate    = db.Column(db.Float)
    max_heartrate        = db.Column(db.Float)
    average_cadence      = db.Column(db.Float)
    calories             = db.Column(db.Float)
    suffer_score         = db.Column(db.Integer)

    # Mapa
    map_polyline         = db.Column(db.Text)
    map_summary_polyline = db.Column(db.Text)

    # Splits/laps (JSON)
    splits_metric        = db.Column(db.JSON)
    laps                 = db.Column(db.JSON)
    streams              = db.Column(db.JSON)   # heartrate[], velocity[], altitude[], cadence[], time[]

    created_at           = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # ── Propriedades calculadas ──
    @property
    def distance_km(self):
        return round(self.distance / 1000, 2) if self.distance else 0

    @property
    def pace_min_km(self):
        """Retorna pace em segundos por km"""
        if self.average_speed and self.average_speed > 0:
            return 1000 / self.average_speed
        return None

    @property
    def pace_str(self):
        """Retorna pace formatado como mm'ss\""""
        secs = self.pace_min_km
        if not secs:
            return '—'
        m = int(secs // 60)
        s = int(secs % 60)
        return f"{m}'{s:02d}\""

    @property
    def moving_time_str(self):
        if not self.moving_time:
            return '—'
        h = self.moving_time // 3600
        m = (self.moving_time % 3600) // 60
        s = self.moving_time % 60
        if h:
            return f"{h}h {m:02d}m"
        return f"{m}m {s:02d}s"

    @property
    def sport_emoji(self):
        emojis = {'Run':'🏃', 'TrailRun':'🌄', 'Walk':'🚶', 'Hike':'🥾', 'Ride':'🚴', 'Swim':'🏊'}
        return emojis.get(self.sport_type, '⚡')

    def to_dict(self):
        return {
            'id': self.id,
            'strava_id': self.strava_id,
            'name': self.name,
            'sport_type': self.sport_type,
            'sport_emoji': self.sport_emoji,
            'start_date_local': self.start_date_local.isoformat() if self.start_date_local else None,
            'distance_km': self.distance_km,
            'moving_time': self.moving_time,
            'moving_time_str': self.moving_time_str,
            'pace_str': self.pace_str,
            'pace_secs': self.pace_min_km,
            'average_speed': self.average_speed,
            'total_elevation_gain': self.total_elevation_gain,
            'average_heartrate': self.average_heartrate,
            'max_heartrate': self.max_heartrate,
            'calories': self.calories,
            'suffer_score': self.suffer_score,
            'splits_metric': self.splits_metric,
            'streams': self.streams,
        }

    def __repr__(self):
        return f'<Activity {self.strava_id} {self.name}>'
