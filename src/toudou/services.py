import csv
import dataclasses
import io
import uuid

from datetime import datetime

from sqlalchemy.exc import NoResultFound
from toudou.models import bulk_insert_todos, get_todos, Todo, get_todo

def import_from_csv(csv_file: io.StringIO) -> None:
    csv_reader = csv.DictReader(csv_file,fieldnames=[f.name for f in dataclasses.fields(Todo)])
    todos = []
    for row in csv_reader:
        try:
            todo = get_todo(uuid.UUID(str(row['id']))) # On verifie si le même id n'existe pas déjà
        except NoResultFound:
            todo = None
        if todo:
            return False
        else:
            todos.append(dict(
                id=uuid.UUID(row['id']),
                task=row['task'],
                complete=row['complete'] == 'True',
                due=datetime.fromisoformat(row['due']) if row['due'] else None
            ))
    bulk_insert_todos(todos)
    return True

def export_to_csv() -> io.StringIO:
    output = io.StringIO()
    csv_writer = csv.DictWriter(
        output,
        fieldnames=[f.name for f in dataclasses.fields(Todo)]
    )
    for todo in get_todos():
        csv_writer.writerow(dataclasses.asdict(todo))
    return output

def export_to_csv_cli(filename: str) -> None:
    with open(filename + ".csv", 'w', newline='') as csvfile:
        csv_writer = csv.DictWriter(
            csvfile,
            fieldnames=[f.name for f in dataclasses.fields(Todo)]
        )
        csv_writer.writeheader()
        for todo in get_todos():
            csv_writer.writerow(dataclasses.asdict(todo))


