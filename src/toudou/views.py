import click
import io
import uuid
import toudou.models as models
import toudou.services as services
import logging

from datetime import datetime
from flask import abort, flash, Flask, redirect, render_template, request, send_file, url_for, Blueprint
from flask_principal import RoleNeed
from flask_login import login_manager, LoginManager, UserMixin
from flask_wtf import FlaskForm
from flask_httpauth import HTTPBasicAuth

from werkzeug.security import generate_password_hash, check_password_hash

from wtforms import (TextAreaField,BooleanField, DateTimeLocalField)
from wtforms.validators import InputRequired, Length
# Connection
auth = HTTPBasicAuth()

admin_role = RoleNeed('admin')
user_role = RoleNeed('user')

users = {
    'john': {'id': 1, 'roles': admin_role, 'password': generate_password_hash('hello')},
    'susan': {'id': 2,'roles': user_role, 'password': generate_password_hash('bye')}
}


# Blueprint
todo_blueprint = Blueprint(
    'todo_blueprint',
    __name__,
    url_prefix='/'
)


# Logging
logging.basicConfig(filename='toudou.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

# Setup Flask-Login
login_manager = LoginManager()
class User(UserMixin):
    def __init__(self, id, name, password):
        self.id = id
        self.name = name
        self.password = password

    def __repr__(self):
        return f'<User {self.name}>'

# Define the user_loader callback
@login_manager.user_loader
def load_user(user_id):
    # Query your database or user storage for a user with the provided user_id
    user = User.query.get(int(user_id))
    return user

@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username).get('password'), password):
        return username
@auth.get_user_roles
def get_user_roles(user):
    if user in users:
        return users[user]['roles']
    return []


class MyForm(FlaskForm):
    task = TextAreaField('task', validators=[InputRequired(), Length(max=200)])
    due = DateTimeLocalField("due", format='%Y-%m-%dT%H:%M')
    complete = BooleanField('complete')



# Web UI
# ======


@todo_blueprint.get('/')
@auth.login_required(role=[admin_role, user_role])
def home():
    return render_template('home.html')


@todo_blueprint.get('/todos')
@auth.login_required(role=[admin_role, user_role])
def todo_get_all():
    return render_template('todo_get_all.html', todos=models.get_todos())


@todo_blueprint.get('/todos/create')
@auth.login_required(role=[admin_role], optional=True)
def todo_create_form():
    user = auth.current_user()
    if user != "john":
        abort(403)
    else:
        form = MyForm()
        if form.validate_on_submit():
            return redirect('/sucess')

    return render_template('todo_create_form.html', form=form)


@todo_blueprint.post('/todos')
def todo_create():
    logging.info('Un nouveau todo a été crée')
    models.create_todo(
        request.form.get('task', '', type=str),
        request.form.get('complete', False, type=bool),
        request.form.get('due', None, type=datetime.fromisoformat)
    )
    flash('Création réalisée avec succès.', 'success')
    return redirect(url_for('.todo_get_all'))


@todo_blueprint.route('/todos/<uuid:id>', methods=['GET', 'POST'])
@auth.login_required(role=[admin_role], optional=True)
def todo_update_form(id: uuid.UUID):
    user = auth.current_user()
    if user != "john":
        abort(403)
    else:
        todo = models.get_todo(id)
        form = MyForm()
        if form.validate_on_submit(): #post
            models.update_todo(
                id,
                request.form.get('task', '', type=str),
                request.form.get('complete', False, type=bool),
                request.form.get('due', None, type=datetime.fromisoformat)
            )
            logging.info(f'Le todo {id} a été modifié')
            flash('Mise à jour réalisée avec succès.', 'success')
        else: #get
            print(form.errors)
            form.task.data = todo.task
            form.complete.data = todo.complete
            form.due.data = todo.due
    return render_template('todo_update_form.html', form=form, todo=todo)


@todo_blueprint.post('/todos/<uuid:id>/delete')
def todo_delete(id: uuid.UUID):
    logging.warning(f'Le todo{id} vient d\'être suprimé')
    models.delete_todo(id)
    flash('Suppression réalisée avec succès.', 'success')
    return redirect(url_for('.todo_get_all'))


@todo_blueprint.get('/csv_import')
@auth.login_required(role=[admin_role], optional=True)
def csv_import_form():
    user = auth.current_user()
    if user != "john":
        abort(403)
    return render_template('csv_import_form.html')


@todo_blueprint.post('/csv_import')
@auth.login_required(role=[admin_role])
def csv_import():
    csv_file = request.files.get('file', None)
    if not csv_file or csv_file.filename == '': # Verify that the file exists
        flash('Aucun fichier trouvé.', 'error')
        return redirect(request.url)
    else:
        if not csv_file.filename.lower().endswith('.csv'): # Verify that the file is in .csv format
            abort(500)
        else:
            if services.import_from_csv(io.TextIOWrapper(csv_file, 'utf-8')): # Verify that the id isn't already in the database
                flash('Tâches importées avec succés', 'success')
                return redirect(url_for('.todo_get_all'))
            else:
                abort(404)


@todo_blueprint.get('/csv_export')
def csv_export():
    return send_file(
        io.BytesIO(services.export_to_csv().getvalue().encode('utf-8')),
        as_attachment=True,
        download_name='export.csv',
        mimetype='text/csv'
    )

#Errorhandler
@todo_blueprint.errorhandler(403)
def access_forbidden(e):
    flash("Vous devez être administrateur pour entrer dans cette page", 'error')
    return redirect(url_for('.todo_get_all'))

@todo_blueprint.errorhandler(404)
def existing_task(error):
    flash('Veuillez importer un fichier .csv, avec des tâches qui ne figurent pas parmis la liste des tâches', 'error')
    return redirect(url_for('.csv_import_form'))

@todo_blueprint.errorhandler(500)
def invalid_csv(error):
    flash('Veuillez importer un fichier .csv valide', 'error')
    return redirect(url_for('.csv_import_form'))


# CLI
# ===


@click.group()
def cli():
    pass


@cli.command()
def init_db():
    models.init_db()


@cli.command()
@click.option('-t', '--task', prompt='Your task', help='The task to remember.')
@click.option('-d', '--due', prompt='Due', type=click.DateTime(), default=None, help='Due date of the task.')
def create(task: str, due: datetime):
    models.create_todo(task, due=due)


@cli.command()
@click.option('--id', required=True, type=click.UUID, help='Todo\'s id.')
def get(id: uuid.UUID):
    click.echo(models.get_todo(id))


@cli.command()
@click.option('--as-csv', is_flag=True, help='Ouput a CSV string.')
def get_all(as_csv: bool):
    if as_csv:
        click.echo(services.export_to_csv().getvalue())
    else:
        click.echo(models.get_todos())


@cli.command()
@click.argument('csv_file', type=click.File('r'))
def import_csv(csv_file):
    services.import_from_csv(csv_file)

@cli.command()
@click.argument('filename')
def export_csv(filename):
    services.export_to_csv_cli(filename)

@cli.command()
@click.option('--id', required=True, type=click.UUID, help='Todo\'s id.')
@click.option('-c', '--complete', required=True, type=click.BOOL, help='Todo is done or not.')
@click.option('-t', '--task', prompt='Your task', help='The task to remember.')
@click.option('-d', '--due', type=click.DateTime(), default=None, help='Due date of the task.')
def update(id: uuid.UUID, complete: bool, task: str, due: datetime):
    models.update_todo(id, task, complete, due)


@cli.command()
@click.option('--id', required=True, type=click.UUID, help='Todo\'s id.')
def delete(id: uuid.UUID):
    models.delete_todo(id)

def create_app():
    global app
    app = Flask(__name__)

    # Importation and register of blueprints
    # from toudou.views import toudou_blueprint
    app.register_blueprint(todo_blueprint)

    # Configuration of the app from prefixed environment variables
    app.config.from_prefixed_env(prefix='TOUDOU_FLASK')
    login_manager.init_app(app)
    return app
