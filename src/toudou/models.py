import uuid

from toudou import config
from dataclasses import asdict, dataclass
from datetime import datetime

from sqlalchemy import delete, insert, select, update
from sqlalchemy import Boolean, Column, DateTime, String, Table, Uuid
from sqlalchemy import create_engine, MetaData


# engine = create_engine('sqlite:///todos.db', echo=True)
engine = create_engine(config['DATABASE_URL'], echo=config['DEBUG'])
metadata = MetaData()

todos_table = Table(
    'todos',
    metadata,
    Column('id', Uuid, primary_key=True, default=uuid.uuid4),
    Column('task', String, nullable=False),
    Column('complete', Boolean, nullable=False),
    Column('due', DateTime, nullable=True)
)


@dataclass
class Todo:
    id: uuid.UUID
    task: str
    complete: bool
    due: datetime | None


def init_db() -> None:
    metadata.create_all(engine)


def create_todo(
    task: str,
    complete: bool = False,
    due: datetime | None = None
) -> uuid.UUID:
    stmt = insert(todos_table).values(
        task=task,
        complete=complete,
        due=due
    )
    with engine.begin() as conn:
        result = conn.execute(stmt)
    return result.inserted_primary_key[0]


def bulk_insert_todos(todos: list[dict]) -> None:
    stmt = insert(todos_table)
    with engine.begin() as conn:
        conn.execute(stmt, todos)


def get_todo(id: uuid.UUID) -> Todo:
    stmt = select(todos_table).where(todos_table.c.id == id)
    with engine.begin() as conn:
        result = conn.execute(stmt).one()
    return Todo(*result)


def get_todos() -> list[Todo]:
    stmt = select(todos_table)
    with engine.begin() as conn:
        result = conn.execute(stmt).all()
    return [Todo(*row) for row in result]


def update_todo(
    id: uuid.UUID,
    task: str,
    complete: bool,
    due: datetime | None
) -> None:
    todo = get_todo(id)
    todo.complete = complete
    todo.task = task
    todo.due = due
    stmt = update(todos_table).where(
        todos_table.c.id == id).values(**asdict(todo))
    with engine.begin() as conn:
        conn.execute(stmt)


def delete_todo(id: uuid.UUID) -> None:
    stmt = delete(todos_table).where(todos_table.c.id == id)
    with engine.begin() as conn:
        conn.execute(stmt)