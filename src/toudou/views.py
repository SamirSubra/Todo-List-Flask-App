import click
import io
import uuid
from datetime import datetime

import toudou.models as models
import toudou.services as services
from flask import abort, flash, Flask, redirect, render_template, request, send_file, url_for, Blueprint
from flask_principal import RoleNeed, UserNeed

from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, IntegerField, BooleanField, RadioField, DateField, DateTimeLocalField)
from wtforms.validators import InputRequired, Length, DataRequired
import logging
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

# Blueprint
todo_blueprint = Blueprint(
    'todo_blueprint',
    __name__,
    url_prefix='/'
)

# Logging
logging.basicConfig(filename='toudou.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

# Connection
auth = HTTPBasicAuth()

# admin_role = RoleNeed('admin')
# user_role = RoleNeed('user')
#
# users = {
#     'john': {'id': 1, 'roles': [admin_role]}, 'password': generate_password_hash('hello'),
#     'susan': {'id': 2,'roles': [user_role]}, 'password': generate_password_hash('bye')
# }


# @auth.verify_password
# def verify_password(username, password):
#     if username in users and \
#             check_password_hash(users.get(username).get('password'), password):
#         return username
#
# @auth.get_user_roles
# def get_user_roles(user):
#     if user in users:
#         return users[user]['roles']
#     else:
#         return []

users = {
    "john": generate_password_hash("hello"),
    "susan": generate_password_hash("bye")
}

@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username

class MyForm(FlaskForm):
    task = TextAreaField('task', validators=[InputRequired(), Length(max=200)])
    due = DateTimeLocalField("due", format='%Y-%m-%dT%H:%M')
    complete = BooleanField('complete')
# Web UI
# ======




@todo_blueprint.get('/')
@auth.login_required
def home():
    logging.warning('Someone has accessed the home page.')
    return render_template('home.html')


@todo_blueprint.get('/todos')
@auth.login_required
def todo_get_all():
    logging.warning('Someone has accessed the list of todos.')
    return render_template('todo_get_all.html', todos=models.get_todos())


@todo_blueprint.get('/todos/create')
# @auth.login_required(role='admin')
@auth.login_required
def todo_create_form():
    form = MyForm()
    if form.validate_on_submit():
        return redirect('/sucess')
    return render_template('todo_create_form.html', form=form)


@todo_blueprint.post('/todos')
def todo_create():
    logging.info('Someone has created a new todo.')
    models.create_todo(
        request.form.get('task', '', type=str),
        request.form.get('complete', False, type=bool),
        request.form.get('due', None, type=datetime.fromisoformat)
    )
    flash('Création réalisée avec succès.', 'success')
    return redirect(url_for('.todo_get_all'))


@todo_blueprint.route('/todos/<uuid:id>', methods=['GET', 'POST'])
@auth.login_required
def todo_update_form(id: uuid.UUID):
    todo = models.get_todo(id)
    form = MyForm()

    if form.validate_on_submit(): #post
        models.update_todo(
            id,
            request.form.get('task', '', type=str),
            request.form.get('complete', False, type=bool),
            request.form.get('due', None, type=datetime.fromisoformat)
        )
        logging.info(f'Someone has updated the todo {id}.')
        flash('Mise à jour réalisée avec succès.', 'success')
    else: #get
        print(form.errors)
        form.task.data = todo.task
        form.complete.data = todo.complete
        form.due.data = todo.due
    return render_template('todo_update_form.html', form=form, todo=todo)


@todo_blueprint.post('/todos/<uuid:id>/delete')
def todo_delete(id: uuid.UUID):
    logging.warning(f'Someone has deleted the todo {id}.')
    models.delete_todo(id)
    flash('Suppression réalisée avec succès.', 'success')
    return redirect(url_for('.todo_get_all'))


@todo_blueprint.get('/csv_import')
@auth.login_required
def csv_import_form():
    return render_template('csv_import_form.html')


@todo_blueprint.post('/csv_import')
@auth.login_required
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
@todo_blueprint.errorhandler(404)
def tache_existante(error):
    flash('Veuillez importer un fichier .csv, avec des tâches qui ne figurent pas parmis la liste des tâches', 'error')
    return redirect(url_for('.csv_import_form'))

@todo_blueprint.errorhandler(500)
def csv_invalide(error):
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
    app = Flask(__name__)

    # Importation and register of blueprints
    # from toudou.views import toudou_blueprint
    app.register_blueprint(todo_blueprint)

    # Configuration of the app from prefixed environment variables
    app.config.from_prefixed_env(prefix='TOUDOU_FLASK')
    # print(app.config)
    return app
