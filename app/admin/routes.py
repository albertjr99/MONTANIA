from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from ..models import db, User, Activity
from ..auth.routes import require_role

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users')
@login_required
@require_role('owner')
def users():
    athletes = User.query.filter_by(role='athlete').order_by(User.name).all()
    managers = User.query.filter_by(role='manager').order_by(User.name).all()
    return render_template('admin/users.html', athletes=athletes, managers=managers)

@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@require_role('owner')
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_owner:
        flash('Não é possível desativar o administrador.', 'danger')
    else:
        user.active = not user.active
        db.session.commit()
        status = 'ativado' if user.active else 'desativado'
        flash(f'Usuário {user.name} {status}.', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@require_role('owner')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_owner:
        abort(403)
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuário {user.name} removido.', 'success')
    return redirect(url_for('admin.users'))
