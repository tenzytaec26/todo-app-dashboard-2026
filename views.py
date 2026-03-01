import random
from flask import Blueprint, render_template, redirect, url_for
from flask import request
from flask import flash
from task import Task
from flask_login import login_required, current_user
from models import db, Task, User, Visit, Waitlist, ActivityLog
# import datetime
import datetime

# Create a blueprint
main_blueprint = Blueprint('main', __name__)


def log_visit(page, user_id):
    """Log a visit to a page by a user."""
    visit = Visit(page=page, user=user_id)
    db.session.add(visit)
    db.session.commit()

@main_blueprint.before_request
def track_visits():
    if request.method == 'GET':
        endpoint = request.endpoint
        if endpoint and endpoint != 'main.dashboard' and not endpoint.startswith('static'):
            user_id=current_user.id if current_user.is_authenticated else None
            log_visit(page=endpoint, user_id=user_id)
###############################################################################
# Routes
###############################################################################


@main_blueprint.route('/', methods=['GET'])
def index():
    # print all visits
    visits = Visit.query.all()
    for visit in visits:
        print(f"Visit: {visit.page}, User ID: {visit.user}, Timestamp: {visit.timestamp}")

    return render_template('index.html')

@main_blueprint.route('/invitation', methods=['GET', 'POST'])
def invitation():

    if request.method == 'POST':
        email = request.form['email']
        # Here you would send a verification email and add to waitlist
        waitlist = Waitlist(email=email)
        db.session.add(waitlist)
        activity_log = ActivityLog(user=current_user.id if current_user.is_authenticated else None, action='waitlist_signup', task_type='waitlist')
        db.session.add(activity_log)
        db.session.commit()
        flash('Invitation sent to ' + email, 'success')

        print(f"Sending invitation to {email}")
        return redirect(url_for('main.invitation'))
    else:
        return render_template('invitation.html')


@main_blueprint.route('/todo', methods=['GET', 'POST'])
@login_required
def todo():
    return render_template('todo.html')


@main_blueprint.route('/dashboard', methods=['GET', 'POST'])
# @login_required
def dashboard():
    visits = Visit.query.order_by(Visit.timestamp.desc()).all()
    users = User.query.all()
    tasks = Task.query.all()
    
    two_week_notes = [random.randint(0, 15) for _ in range(7)]
    total_users = User.query.count()
    last6_days = created_a=datetime.datetime.now()-datetime.timedelta(days=7)
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    new_users = User.query.filter(User.created_at >= last6_days).count()
    visits_today = Visit.query.filter(Visit.timestamp >= today).count()
    productivity_change = (visits_today / len(visits)) * 100 if len(visits) > 0 else 0
    waitlist_signups = Waitlist.query.filter(Waitlist.timestamp >= last6_days).count()
    chart_week = [(today - datetime.timedelta(days=i)).strftime("%a") for i in range(6, -1, -1)]

    week_notes = [0, 0, 0, 0, 0, 0, 0]
    two_week_notes = [0, 0, 0, 0, 0, 0, 0]

    two_weeks_ago = today - datetime.timedelta(days=14)
    index_visits = Visit.query.filter(Visit.page == 'main.index', Visit.timestamp >= two_weeks_ago).all()
    week_visits = [0, 0, 0, 0, 0, 0, 0]
    two_week_visits = [0, 0, 0, 0, 0, 0, 0]
    for visit in index_visits:
        days_ago = (today-visit.timestamp).days
        if 0<= days_ago < 7:
            week_visits[6 - days_ago] += 1
        elif 7<= days_ago < 14:
            two_week_visits[13 - days_ago] += 1

    tracked_pages = ["main.index", "auth.login", "main.invitation", "auth.sign-up", "auth.signup", "main.todo"]
    page_visits = []
    

    for page in tracked_pages:
        count = Visit.query.filter(Visit.page == page, Visit.timestamp >= today).count()
        page_visits.append(count)

    errors = ActivityLog.query.filter(ActivityLog.task_type == 'error').order_by(ActivityLog.timestamp.desc()).all()
    return render_template('admin.html',
                           date=datetime.datetime.now().strftime("%B %d, %Y"),
                           total_users=total_users,     # add real number
                           new_users=new_users,         # add real number
                           visits_today=visits_today,    # add real number
                           productivity_change=productivity_change,   # add real number
                           visits=visits,           # add real value
                           chart_week=chart_week,   # update list to show today as the last day in the chart
                           week_notes=week_notes,   # add real values
                           week_visits=week_visits,
                           two_week_visits=two_week_visits,
                           two_week_notes=two_week_notes,  # add real values
                           waitlist_signups=waitlist_signups,
                           users=users,
                           tasks=tasks,
                           page_visits=page_visits, 
                           errors=errors
                           )



@main_blueprint.route('/api/v1/tasks', methods=['GET'])
@login_required
def api_get_tasks():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return {
        "tasks": [task.to_dict() for task in tasks]
    }


@main_blueprint.route('/api/v1/tasks', methods=['POST'])
@login_required
def api_create_task():
    data = request.get_json()

    new_task = Task(title=data['title'], user_id=current_user.id)
    db.session.add(new_task)

    activity_log = ActivityLog(user=current_user.id, action='create', task_type='todo')
    db.session.add(activity_log)

    db.session.commit()
    return {
        "task": new_task.to_dict()
    }, 201


@main_blueprint.route('/api/v1/tasks/<int:task_id>', methods=['PATCH'])
@login_required
def api_toggle_task(task_id):
    task = Task.query.get(task_id)

    if task is None:
        return {"error": "Task not found"}, 404

    activity_log = ActivityLog(user=current_user.id, action='toggle', task_type='todo')
    db.session.add(activity_log)    

    task.toggle()
    db.session.commit()

    return {"task": task.to_dict()}, 200


@main_blueprint.route('/remove/<int:task_id>')
@login_required
def remove(task_id):
    task = Task.query.get(task_id)

    if task is None:
        return redirect(url_for('main.todo'))

    activity_log = ActivityLog(user=current_user.id, action='delete', task_type='todo')
    db.session.add(activity_log)  

    db.session.delete(task)
    db.session.commit()

    return redirect(url_for('main.todo'))