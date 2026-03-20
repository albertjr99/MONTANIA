from flask import Blueprint, render_template, redirect, url_for, abort, request
from flask_login import login_required, current_user
from ..models import User, Activity

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/home')
@login_required
def home():
    return render_template('dashboard/index.html')

@dashboard_bp.route('/athlete/<int:user_id>')
@login_required
def athlete(user_id):
    if not current_user.is_manager and current_user.id != user_id:
        abort(403)
    athlete = User.query.get_or_404(user_id)
    return render_template('dashboard/index.html', target_athlete=athlete)

@dashboard_bp.route('/group')
@login_required
def group():
    if not current_user.is_manager:
        abort(403)
    return render_template('dashboard/group.html')

@dashboard_bp.route('/activity/<int:activity_id>')
@login_required
def activity(activity_id):
    act = Activity.query.get_or_404(activity_id)
    if act.user_id != current_user.id and not current_user.is_manager:
        abort(403)
    return render_template('dashboard/activity.html', activity=act)

@dashboard_bp.route('/settings')
@login_required
def settings():
    return render_template('dashboard/settings.html')
