from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from .models import db, User
from .config import config
import os

login_manager = LoginManager()
migrate       = Migrate()

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config[config_name])

    # Extensões
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view        = 'auth.login'
    login_manager.login_message     = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Blueprints
    from .auth.routes      import auth_bp
    from .strava.routes    import strava_bp
    from .dashboard.routes import dashboard_bp
    from .admin.routes     import admin_bp
    from .api.routes       import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(strava_bp,    url_prefix='/strava')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(admin_bp,     url_prefix='/admin')
    app.register_blueprint(api_bp,       url_prefix='/api')

    # Redirecionar raiz para dashboard
    from flask import redirect, url_for
    @app.route('/')
    def index():
        return redirect(url_for('dashboard.home'))

    # Criar tabelas e owner padrão na primeira execução
    with app.app_context():
        db.create_all()
        _seed_owner(app)

    return app


def _seed_owner(app):
    """Cria o usuário owner padrão se não existir nenhum."""
    from .models import User
    if not User.query.filter_by(role='owner').first():
        owner = User(name='Admin Montania', email='admin@montania.com', role='owner')
        owner.set_password('montania@2024')
        db.session.add(owner)
        db.session.commit()
        print("✅ Owner padrão criado: admin@montania.com / montania@2024")
        print("   ⚠️  Troque a senha após o primeiro login!")
