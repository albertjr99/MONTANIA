import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-mude-em-producao')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///montania.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    STRAVA_CLIENT_ID     = os.environ.get('STRAVA_CLIENT_ID')
    STRAVA_CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')
    STRAVA_VERIFY_TOKEN  = os.environ.get('STRAVA_VERIFY_TOKEN', 'montania_webhook_2024')
    APP_BASE_URL         = os.environ.get('APP_BASE_URL', 'http://localhost:5000')

    STRAVA_AUTH_URL      = 'https://www.strava.com/oauth/authorize'
    STRAVA_TOKEN_URL     = 'https://www.strava.com/oauth/token'
    STRAVA_API_BASE      = 'https://www.strava.com/api/v3'
    STRAVA_SCOPE         = 'read,activity:read_all,profile:read_all'

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}
