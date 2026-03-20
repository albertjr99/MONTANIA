from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ..models import db, User

auth_bp = Blueprint('auth', __name__)

def require_role(*roles):
    """Decorador para restringir acesso por role."""
    from functools import wraps
    from flask import abort
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        user = User.query.filter_by(email=email).first()

        if user and user.active and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash(f'Bem-vinda, {user.name.split()[0]}! 🏔️', 'success')
            return redirect(next_page or url_for('dashboard.home'))

        flash('E-mail ou senha incorretos.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu com segurança.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    """Apenas owner pode registrar novas atletas/gestores."""
    if not current_user.is_owner:
        flash('Acesso restrito ao administrador.', 'danger')
        return redirect(url_for('dashboard.home'))

    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role     = request.form.get('role', 'athlete')

        if not all([name, email, password]):
            flash('Preencha todos os campos.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('E-mail já cadastrado.', 'danger')
        elif role not in ('owner', 'manager', 'athlete'):
            flash('Role inválido.', 'danger')
        else:
            user = User(name=name, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f'Usuário {name} criado com sucesso!', 'success')
            return redirect(url_for('admin.users'))

    return render_template('admin/register.html')


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_pw = request.form.get('current_password')
    new_pw     = request.form.get('new_password')
    confirm_pw = request.form.get('confirm_password')

    if not current_user.check_password(current_pw):
        flash('Senha atual incorreta.', 'danger')
    elif new_pw != confirm_pw:
        flash('As novas senhas não coincidem.', 'danger')
    elif len(new_pw) < 6:
        flash('A nova senha deve ter pelo menos 6 caracteres.', 'danger')
    else:
        current_user.set_password(new_pw)
        db.session.commit()
        flash('Senha alterada com sucesso!', 'success')

    return redirect(url_for('dashboard.settings'))
