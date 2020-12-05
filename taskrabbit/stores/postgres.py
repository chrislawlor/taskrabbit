import logging
from typing import Iterable, Optional

import psycopg2 as pg

from .base import StoredTask, TaskStore

# TODO: configuration
DSN = "postgresql://taskrabbit:password@localhost:5432/taskrabbit"


class PostgresTaskStore(TaskStore):
    def __init__(self):
        self.conn = pg.connect(dsn=DSN)
        self.create_table()

    def create_table(self):
        with self.conn.cursor() as c:
            c.execute(
                """
            CREATE TABLE IF NOT EXISTS tasks (
                id text UNIQUE NOT NULL
                , task text
                , args text
                , kwargs text
                , task_data json
            )
            """
            )

    def execute(self, query: str, *params) -> pg.extensions.cursor:
        c = self.conn.cursor()
        try:
            c.execute(query, params)
            self.conn.commit()
        except Exception as e:
            logging.exception(e)
            self.conn.rollback()
            raise
        return c

    def save(self, task: StoredTask):
        self.execute(
            """
            INSERT INTO tasks
            VALUES
                (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """,
            task.id,
            task.task,
            task.argsrepr,
            task.kwargsrepr,
            task.json(),
        )

    def delete(self, task: StoredTask):
        self.execute(
            """
        DELETE FROM tasks
        WHERE id=%s
        """,
            task.id,
        )

    def load_tasks(self, task_name: Optional[str] = None) -> Iterable[StoredTask]:
        if task_name is None:
            logging.debug("loading tasks")
            cursor = self.execute("SELECT task_data FROM tasks")
        else:
            logging.debug("loading tasks with task name: %s", task_name)
            cursor = self.execute(
                "SELECT task_data FROM tasks WHERE task=%s", task_name
            )
        for row in cursor.fetchall():
            logging.debug(f"{row=}")
            yield StoredTask(**row[0])
