import logging
import sqlite3
from typing import Iterable, Optional

from .base import TaskStore, StoredTask


class SqliteTaskStore(TaskStore):
    def __init__(self, dbname="tasks.sqlite"):
        super().__init__()
        self.conn = sqlite3.connect(dbname)
        self.conn.row_factory = sqlite3.Row
        self.create_table()

        # execute many writes 1000x faster by not waiting for
        # each transaction to go to disk.
        # See https://www.sqlite.org/faq.html#q19
        self.execute("PRAGMA synchronous=OFF")

    def create_table(self):
        self.execute(
            """
        CREATE TABLE IF NOT EXISTS tasks (
            id text UNIQUE NOT NULL
            , task text
            , args text
            , kwargs text
            , json text
        )
        """
        )

    def execute(self, query: str, *params) -> sqlite3.Cursor:
        c = self.conn.cursor()
        try:
            c.execute(query, params)
            self.conn.commit()
        except Exception as e:
            logging.exception(e)
            raise
        return c

    def save(self, task: StoredTask):
        self.execute(
            """
        INSERT INTO tasks
        VALUES
            (?, ?, ?, ?, ?)
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
        WHERE id=?""",
            task.id,
        )

    def load_tasks(self, task_name: Optional[str] = None) -> Iterable[StoredTask]:
        if task_name is None:
            logging.debug("loading tasks")
            cursor = self.execute("SELECT * FROM tasks")
        else:
            logging.debug("loading tasks with task name: '%s'", task_name)
            cursor = self.execute("SELECT * FROM tasks WHERE task=?", task_name)
        for row in cursor.fetchall():
            yield StoredTask.from_string(row["json"])
