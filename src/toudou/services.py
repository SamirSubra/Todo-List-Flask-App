import csv
import dataclasses
import io
import uuid

from datetime import datetime

from toudou.models import bulk_insert_todos, get_todos, Todo

def export_to_csv() -> io.StringIO:
    output = io.StringIO()
    csv_writer = csv.DictWriter(
        output,
        fieldnames=[f.name for f in dataclasses.fields(Todo)]
    )
    for todo in get_todos():
        csv_writer.writerow(dataclasses.asdict(todo))
    return output


def import_from_csv(csv_file: io.StringIO) -> None:
    csv_reader = csv.DictReader(
        csv_file,
        fieldnames=[f.name for f in dataclasses.fields(Todo)]
    )
    todos = []
    for row in csv_reader:
        todos.append(dict(
            id=uuid.UUID(row['id']),
            task=row['task'],
            complete=row['complete'] == 'True',
            due=datetime.fromisoformat(row['due']) if row['due'] else None
        ))
    bulk_insert_todos(todos)
