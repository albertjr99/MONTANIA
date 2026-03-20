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
    # Filtro de data em pt-BR / Brasília
    import pytz
    from datetime import datetime as _dt
    _tz_br = pytz.timezone('America/Sao_Paulo')

    @app.template_filter('dtbr')
    def format_dt_brasilia(value, fmt='%d/%m/%Y %H:%M'):
        """Formata datetime para horário de Brasília."""
        if not value:
            return '—'
        if isinstance(value, str):
            try:
                value = _dt.fromisoformat(value)
            except Exception:
                return value
        if value.tzinfo is None:
            # Assume UTC e converte
            value = pytz.utc.localize(value).astimezone(_tz_br)
        else:
            value = value.astimezone(_tz_br)
        MONTHS = ['','Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
        DAYS   = ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom']
        day_name = DAYS[value.weekday()]
        return f"{day_name}, {value.day:02d} {MONTHS[value.month]} · {value.strftime('%H:%M')}"



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

    @app.context_processor
    def inject_globals():
        """Injeta variáveis globais em todos os templates."""
        import pytz
        from datetime import datetime
        tz = pytz.timezone('America/Sao_Paulo')
        now = datetime.now(tz)
        return dict(
            LOGO_B64="data:image/png;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/4gHYSUNDX1BST0ZJTEUAAQEAAAHIAAAAAAQwAABtbnRyUkdCIFhZWiAH4AABAAEAAAAAAABhY3NwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAA9tYAAQAAAADTLQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAlkZXNjAAAA8AAAACRyWFlaAAABFAAAABRnWFlaAAABKAAAABRiWFlaAAABPAAAABR3dHB0AAABUAAAABRyVFJDAAABZAAAAChnVFJDAAABZAAAAChiVFJDAAABZAAAAChjcHJ0AAABjAAAADxtbHVjAAAAAAAAAAEAAAAMZW5VUwAAAAgAAAAcAHMAUgBHAEJYWVogAAAAAAAAb6IAADj1AAADkFhZWiAAAAAAAABimQAAt4UAABjaWFlaIAAAAAAAACSgAAAPhAAAts9YWVogAAAAAAAA9tYAAQAAAADTLXBhcmEAAAAAAAQAAAACZmYAAPKnAAANWQAAE9AAAApbAAAAAAAAAABtbHVjAAAAAAAAAAEAAAAMZW5VUwAAACAAAAAcAEcAbwBvAGcAbABlACAASQBuAGMALgAgADIAMAAxADb/2wBDAAUDBAQEAwUEBAQFBQUGBwwIBwcHBw8LCwkMEQ8SEhEPERETFhwXExQaFRERGCEYGh0dHx8fExciJCIeJBweHx7/2wBDAQUFBQcGBw4ICA4eFBEUHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh7/wAARCACRATgDASIAAhEBAxEB/8QAGgABAQADAQEAAAAAAAAAAAAAAAUDBAYCAf/EAE8QAAEDAwIDAwYJBwkFCQAAAAEAAgMEBREGIRIxQRNRYSI2cXSBsxQVIzIzQmKRoQcWJDRScrEmNVNUgpKytMQlQ0VzdUZVY2RlosHC0f/EABoBAQEBAQEBAQAAAAAAAAAAAAABAgUDBAb/xAAnEQEBAAIBBAEEAgMBAAAAAAAAAQIREgUhMTJhA0FRcQTwEyLRgf/aAAwDAQACEQMRAD8AnoiL9S/SiIiAiIgIiICIiAiIgIiICIiAiIgJvjOFvWC11F5usNvpyGF+TJK/ZkLBu57j0aACT+G66kaktArhp7sM6VLewLuzHa8Wf1rOM8fFvj9nycLGeerqMZZ6uo4hFvX22VFnus9vqSxz4j5MjDlkjCMte0jYtc0gj0rRW5ZZuNS7mxERFEREBERAREQEREBERAREQEREErWHmlePUJ/duRNYeaV49Qn925Fy+oe0cjqXtiqoiLquuIiICIiAiIgIiICIiAiIgIi3rHbKm73KOipuFpIL5JHnDIo2jLpHno0Dcn2DchS2SbqW6aKLobrabRNa57hp2orKiOikEdU2oDQ4tccNmYAPmE7YOS0luee3rSsEFuo5dU3CJkkVO/s6CCTlUVOMgkdWM2ce84HUrH+Sa3GOc1tlun8mrB8TMBbdrixr7i760EOzmQeBOz38vqt33XLrLV1E9XUy1VTK6WeV5fI9xyXOJySfasSuGPGfLWOOo6m3/wAptOm2PPFeLXG59C4/OqKcZc+HPMlm7m89i4LllmoqqooqyGspJXQ1ELxJHI3m1wOQVb1ZTU1VBDqa3RshpK15ZUQt2FNU4y5ng1w8pvhkfVWZOGWvtWfW/Fc8iu1ulbrR259ZL8Gc6JjJailbLmopmPxwukZjyQcjqcZGcKEt45TLw3MpfAiItKIiICIiAiIgIiICIiAiIglaw80rx6hP7tyJrDzSvHqE/u3IuV1D2jkdR9sVVERdV1xERAREQEREBERAREQERFB6hjkmlZFExz5HuDWtaMlxOwAHUror1JHYbbJp2kex1bKQbrOx2RkbinaeXC07uI5u25NCNb+a1GJnjF+qI8xt60Ebh8490rgdhzYDnmRjnWMfJK2KNrnyPIaxoGS4nkB37rz9rv7R575X4XvyeiqdqeEQ8Bpyxwr+0+i+C4+W7T7PD+OMb4Wvqq6w3KsjhoYnQWujZ2NDA7m1mclzvtuOXOPecdAty+SR2K1O01TFr6uVzX3WZpz5Q3bTgjbhYd3d7vBoXNqY48sud/vyYzd5CIi9noLoNC32Oy3XgrGtkttSWtqWOZxhpacslDermOw4DqMjqufRZyxmU1WcsZlNVcqai8ae1XNUTztnrWvc6SRx7SOqY/ck/tMe0+0HovmpLdTNhhvdoa74pq3EBpPEaWUbuhee8c2k8278wVsUIdqKxNthy+6W2Nz6I/WngG74fS3d7eexcO5aWm7tHb5poK2F1VbatojrIQ7Bc0HLXNPR7SctPpHIleU3/wCx5zfmeYkoqmo7O+01MZjmFVQ1LO1o6pow2aP0dHDk5vMH2KWvaWWbj1llm4IiKqIiICIiAiIgIiICIiCVrDzSvHqE/u3ImsPNK8eoT+7ci5XUPaOR1H2xVURF1XXEREBERAREQEREBEWahpZ66sho6WPtJ5nhkbcgZJ8TsPaolYQCSABkk4wF0zIIdKRipro2S35w4qekfgiiHSSQHnJ1azpzd0C+Cqt+mRw2yeG4XnGHVjBxQ0p69jn57/t8h9XvXOSyPke6SR7nvc4uc5xyXE8yT1WO+f6Y9v09PfNU1DnvL5p5X5JJJc9xP4kkrpWtbpCHje4O1FKzyIxuLe0jm4/0xB2H1BufKwBzdLUT0tRHUU00kM0buJkkbi1zT3gjcLG4lzi5xLnE5JJySVcsd9vstx32+z4d9zuip2iw3K5wuqIYmQ0jDiSrqHiKFh7i87E+AyfBb3wbSdBkVNfXXiYfUo4xDFnu7SQFx9jAlzk7QuUnaOeyEwe5dAy+2mnP6HpG14HI1cs07vb5Yb+C9fnXn/s1poDu+LgfxJynLL8HLL8OdRdC7UNtn2q9I2Zw6mB00B9ha/A+5ODSFfkMludlmd83tAKqEe0BrwPY5TnZ5hzv3iFSzzUtTFU00r4ponh8b2nBa4HIIXQXekp75Qy3+1MYypjaX3OiYMGI9Zox1jJO4HzCf2SCtW4aauVNSOrqYwXKgb86pon9o1n7w+cz+0Ao8ckkZJje9hLS0lpIyCMEeghO2XfGp7d4sWG8QwUslpu0UlTaZn8bmsI7Snfy7WInk7vHJw2PeMF+s01qdFK2WOroKgF1LWRfRzN/+rh1adwfYTMVSyXqe2skpnxR1dvnINRRzZ7OTxGN2uHRwwR6NkuNl3iurLuJaLo32GkuwM+l6kzuxl9unc1tSzv4eko/d8r7K56Rj45HRyNcx7SWua4YII5ghaxymSzKV5REWmhERAREQEREBERBK1h5pXj1Cf3bkTWHmlePUJ/duRcrqHtHI6j7YqqIi6rriIiAiIgIiICIiAnpREFO2/EEdMJbj8ZVFRk/o8HBEzHeZDxE+gM9qzyXazsd+jaWoeH/AMxVVEjj6S17B+CiqlbLBe7lH2tDaa2eLP0rYTwf3uX4rzuM82sWSd7Wy25WGccNXpxsIP16KtkYRv8A+J2gP4LNT2ejq5459O1rK6WN4d8X1sYjmdg5AAyWSjwa7iP7K0btp+82qBs9fb5oYXO4RLs5nF3cQJGfBTFJjLN41Nb9ao3653a41pF1lkEkJLGwOZ2bYPstjwAz0ABTldh1A2qhZS6hpPjOFjeFk3HwVMQHLhk34h9l4cO7C9fEdurfLs9+o3Z5QV5FLKPDJ+Td7HexJlMe1mllmPmICK67R+ptzFZ6ioaPr0+Jmn0FhIKhbjYjBW5lL4amUvgREWlbNur623VbKuhqpaadnJ8bi0+jborPxvZbsHC/Wx0FUR+vW1rWOJxzfCcMd6Wlh9K51ZqKmnrayGjpYnSzzvEcbBzc4nACxljL3rGWM8uhl0dPNSQVtou1tr6aoe5sIfMKWZ3Dji8iXhBwSB5JcPFYnaH1Y0ZFiqnt74+F4+9pIWHWVTTurqe10Uolo7XCKWN7fmyvyXSSD955cR4YUPphYw52b2zjys8vcsckE74pAWSxPLXDq1wOCPvXgkkkkkk8yeqIvWPTQiIqoiIgIiICIiAiIglaw80rx6hP7tyJrDzSvHqE/u3IuV1D2jkdR9sVVERdV1xERAREQEREBERAREQFnqqysqooYqqrqJ44GhkTJJC4MaBgAAnYeAWBFLJUs2qacurbXVSMqITUW6qZ2VbTZwJGZzkdz2ndp6EdxOWorQ+11EUkcnwm31TTJR1bR5MzP/hw5OadwfYTLVax3p1DBJQVdOK61zu4pqV7uHDuQkY76jwOo5jYghYssu4zZZdxJRdDUabNZE+s0zO6607RxPpw0CrgGQPLjG7huPKZkehc91I7tlrHKVccpTAO5AyiIq0Ii3rPaLld6gw26kknLd5HjAZEP2nuOzRsdyQEtk8pbJ5aK6aNg0vbHTyO4b/WxFsMePKooHDynu7pHg4A5taSTgkY+xzWjTPl0ksF4vI+bUAcVLSnvZn6V46O+aOnFhc3UTS1E8k88r5ZZHFz3vOXOJ5knvXn7/pj3/TwiIvV6CIiAiIgIiICIiAiIgIiIJWsPNK8eoT+7ciaw80rx6hP7tyLldQ9o5HUfbFVREXVdcREQEREBEQbnAyT4ICIiAiY2B6FEBFQtFkut2bI+30T5YovpJS5rI2eDnuIaD6StwaTvr2uNNTU9YWjJZR1sNQ8f2I3lx9gWLnjLq1nljO20NF9e1zHuY9pa5pLXNIwQRzB8UaC4kNBcQCcAZ2G5K009RSyQzMmhkfHKw8THtcQ5p7wRyKujVVVUt4L3Q0N6GA3tKqPE+P+awtefaSufXqN/ZSslDWu4HB2HDLTjoR1CzljL5ZuMq98J0dO7iltN5o88209ayRo9HHHn8UzooNJEeo3no3jgb+OD/BZa6/3CjqpKWrsFihniPC9jrXEC093JbdXemR6Wt9e2yWMVM1XUxSO+L2YLWNhLem30jl5Xc1/15d5r/rQZedPUfC636WZNK3lJcat0wP9hgY37wVpXbUF2ukDaapqeCkYcspYGCKBnoY0BufHGVnl1JPJE+M2mxtD2lpc23xhwz3HGx8VGjjke2RzGOc2Noc8gZDRkDJ9pA9JC9McZ5sbxx+9jyiL6xrnuDWNc5x5ADJK29HxERARZqqlqKV7GVMTonPjbK0OHNjgHNPoIIKVFLUU8cEk8L42zx9pESPnNyW5HhlpHsTcTcYURexFIYXTBjjG1wY5+DgOIJAz3kNP3HuRXhERUEREBERAREQStYeaV49Qn925E1h5pXj1Cf3bkXK6h7RyOo+2KqiIuq64iIgIiIC6LQT6OnudZcK+n+E09HQSySQ5xxtfwwkA9D8rsudVq0cMWlr7U/XeaakHoe8y/wCnC8/qd8dflj6nrpp363G13WajEglibh0Mo5SxuAcx49LSD7VogEkAAknkB1V13+1tLNfnNZaMMPe+le7bx8iR2PRIOjV40u0UZqL9MwFlvAMAcMh9S7PZDHXGHPPgzHVSZWY9/MSZanyp6ooqWl0nR0cAaam1Vr4K54OeKaaNriPDh7FzPEsJUfS9thuV04at746GnifU1b2fOETBk48ScNHi4LNaz8J0vfonvcZIn01dxOOS7he6I58c1A+5ZdLNc+zakhiyJTbmvG+CWMqInP8A/aCfQCsbuONn97sy2Y1pX69VV2kYx4bT0UHk0tHEfkoG9wHU97juTuVNjc5kjXscWPactcOYPeF8GCMjki9pjJNPWTXZ08k51RZKuarw+9W2ETGf61VTghruPvezIPFzLc5zjKw/k7lMGrIZ+yjl7Klq39nIMsdillOCOoONwvmhwRW3KZ20MVorHS9xBhcwD+85v4LxoXzi3/qVb/lJl45dscsXjl4yjzfrfTPpm3uztd8XTO4ZYS7idSSn/duPMtO5a7qAeoKhu5EKjYrpJa6lzzCypppm9lVU0h8iePO7T3HqHc2kAjksuo7XDRdlW26d9VaqvJppngB7SPnRyAbB7c4ONjsRsQty3G8a3Lce1bv5Sc/n1ds/1grXr/Mm0+v1nu6ZbH5SvPq7+sFYK8fyItB76+t/wUyzj64/37Mz1xRF29imobHZ6S2XNjQ3UILq6QtBdT0xy2F4zyIeTL4hje9c9pK1C836nopZBDTby1UxOBFC0Ze4k7DYYBO2SFVv1qr7team4Or7FEJX/JxC6wYjjADWMHlcg0AexPqWZXjafUst41zlyo6i3XGooKpnBPTyOikb3FpwVU0AAdc2LI/4hB7wKhrOgnks9uvUs9JUVDWCjrjTVLJgHMb8k9xaTu6NuDnrGT1U/wDJ/wCfViH/AKjB7xqvLl9O34q8uWFrNf6SluVPPfbVC2Hgdi4UbOUDicCRg/o3H+6TjkQudG/Jb9Bcam13Y1lKWF7XOa5j28TJGHIcx7frNIJBC2r3b6U0sd5s4ebdM/gfE53E+kl59k49R1a76w57gq4249r4XHc7Vsa6/nG3eNpof8vGmrv5s01/0n/Uzr7rvBuFux/3RQ/5di+av/mzTP8A0j/UzrOHjFnHxi55d9DFTQ0cOgZY421VZB8IkkcBmOvcA6GPJG2GgRnfnK7uUT8n9tjrb06tqRAKO3RmplM8gjje8fRxlziAOJ/CN+nEvtTY7rU18tfLebKaqWUyvlbd4A4vJyXDy9jndT6lmV1vwZ2W634c44FpIcCCNiCMEFfF0/5QqLhr4Lw2SmkFyZ2tQaaVskbKkY7Zoc0kbkh/PYPA6LmF7YZcpt6YXc2IiLTQiIgIiIJWsPNK8eoT+7ciaw80rx6hP7tyLldQ9o5HUfbFVREXVdcREQEREBWnSRRaEjiB+Vqro5zx3CGJvD7933KKmN87LNm2bNt+wXAWy6RVMkXbU5DoqmHP0sLwWyM9rScHocHotzU8tDTdjZbTWNrKGlLpDUtbwiolfjL8dMNDGY+yT1URFLhLlyS4y3azpZ8RddaSUhoqrZM0EnHlR4nA9phA9q07JcprRdIa+BrJHRkh0bxlkjCCHMcOoIJB9K0sIrxnf5Xj5dFU6fZcnmq0s810L8uNEXfpVP8AZLOcg7ntznrgrBFpHUriXTWWso4m7vmrIzTxMHeXyYaB7VEODz3Rx4iC45I5ZPJZ45ztKzrKeKv3KqorXaZbJa6htXLUFpr6xgIY/hOWxR5wSwHcuI8ogY2Azj0S9rL+HPc1o+B1gyTjc0soH4lRE6Jw/wBbPyvDtYKrYbpHSCahuEb6i11eBUwg+U0jlIwnk9uTjodwdipSLWUmU01ZMpqreu6umr9X3Kro5hNTzTF8Ug+s0gYXq4Y/MWzd/wAOrf8ABT//AIoXtTfA3O3LdTh2k/DPHtJ+F9kkdr0c5rHNNbeH4duOKOmjdyO2RxyD7ox3qB9yAAcsBFccdLjNLekaiF1XPaKyVsdHdI/g73vOGxSZzFIf3X4z4Fy96JaaTXtnbU4idDcYRJxH5pEgzkqD9yYGMdPSs3De/lLjvfy9z4MzyP2j/Fbtiuj7ZVPc6JtTSTM7OqpnnDZo+7wIO4dzBAKnotXGWaq63NVf1zV26ru9PJapny0jKGmhjdIAH+RE1mHAbBwI3/DbCaseyS26bax7XFlq4XYOcH4ROcfcQoCAAcsLMw1JPwkw1r4dBeZI7dpuhssJaZ6jhr68g5wXD5GM/usPER0MvgufQAAYGEWsceMXGai9pt7K6219gmc0GZvwqjLiAG1EYPk/22cTfTwKCDlDuMIkx1aSatERFpoQ7YB68vFZ+zjiAM/EX8xED/E9PRzI7tihqZuBzI39kxw4XMj8kOHcf2vbkqbTZLR1kWO1pKhmeXFE4Z/BfHUlU2EzupZ2xDm8xkNHtWHly2QbEEcxyTuJWr99JXjH9Qn925Fn1nUyy6TvZmImc6gmy6QZdtG7Hlc9u7OEXL6h7Ryeo+2LyiIvZ9oiIgIiICIisBERQERFQREUBERWIIiKKIiKwEREoIiKAiIgIiICIitBERICy0X67B++P4hEUCt/X6n/AJzv4lYkREx8CIi0qZqvzWu3qU3+AoiL4P5PmOd/N9o//9k=",
            current_year=now.year,
        )

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
