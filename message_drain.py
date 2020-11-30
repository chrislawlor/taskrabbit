import argparse
import json
import logging
import os
import socket
import sqlite3
import termtables
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from kombu import Connection, Exchange, Message, Queue

USERNAME = "guest"
PASSWORD = "guest"
HOST = "rabbit"
PORT = 5672
VHOST = "/"
EXCHANGE = "default"
DEFAULT_LOG_LEVEL = "INFO"

# Sets kombu Consumer prefetch count
# See https://docs.celeryproject.org/projects/kombu/en/stable/userguide/consumers.html#reference  # noqa
CONSUMER_PREFETCH_COUNT = 10

URL = f"amqp://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{VHOST}"


_exchange = Exchange(EXCHANGE, "direct", durable=True)


@dataclass
class StoredTask:
    headers: Dict[str, Any]
    body: Any

    def json(self):
        return json.dumps({"headers": self.headers, "body": self.body}, indent=2)

    @classmethod
    def from_string(cls, string):
        data = json.loads(string)
        return cls(**data)

    @classmethod
    def from_message(cls, message: Message):
        # Kombu docs say message.body is a str, but it's really a memoryview,
        # which is not JSON serializable
        return cls(body=message.decode(), headers=message.headers)

    @property
    def id(self):
        return self.headers["id"]

    @property
    def task(self):
        return self.headers["task"]

    @property
    def argsrepr(self):
        return self.headers["argsrepr"]

    @property
    def kwargsrepr(self):
        return self.headers["kwargsrepr"]

    def __repr__(self):
        return f"<StoredTask {self.task}: {self.id}>"


class TaskStore(ABC):
    @abstractmethod
    def save(self, task: StoredTask):
        ...

    @abstractmethod
    def load_tasks(self, task_name=Optional[str]) -> Iterable[StoredTask]:
        ...

    @abstractmethod
    def delete(self, task: StoredTask):
        ...


class FileTaskStore(TaskStore):
    def __init__(self, directory):
        self.path = Path() / directory
        self.path.mkdir(parents=True, exist_ok=True)

    def save(self, task: StoredTask):
        with open(self.path / task.id, "w") as f:
            f.write(task.json())

    def load_tasks(self, task_name: Optional[str] = None) -> Iterable[StoredTask]:
        for path in self.path.glob("*"):
            with open(path) as f:
                data = f.read()
                task = StoredTask.from_string(data)
                if task_name is None or task.task == task_name:
                    yield task

    def delete(self, task: StoredTask):
        try:
            os.remove(self.path / task.id)
        except FileNotFoundError:
            pass


class SqliteTaskStore(TaskStore):
    def __init__(self, dbname="tasks.sqlite"):
        super().__init__()
        self.conn = sqlite3.connect(dbname)
        self.conn.row_factory = sqlite3.Row
        self.create_table()

    def create_table(self):
        self.execute(
            """
        CREATE TABLE IF NOT EXISTS tasks
        (id text, task text, args text, kwargs text, json text)
        """
        )

    def execute(self, query: str, *params) -> sqlite3.Cursor:
        c = self.conn.cursor()
        try:
            c.execute(query, params)
            self.conn.commit()
        except Exception as e:
            logging.exception(e)
        return c

    def save(self, task: StoredTask):
        self.execute(
            """
        INSERT INTO tasks
        VALUES
        (?, ?, ?, ?, ?)
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


class TaskCounter(Counter):
    def stream(self, tasks: Iterable[StoredTask]):
        for task in tasks:
            self.update([task.task])
            yield task

    def display(self):
        if self:
            termtables.print(self.most_common(), header=["Task", "Count"])


def fill(
    queue: Queue, store: TaskStore, routing_key: str, task_name: Optional[str] = None
) -> None:
    # Uncomment this to fill tasks to a different queue
    # queue = Queue("fill", exchange=_exchange, routing_key=ROUTING_KEY)
    logging.info(f"Filling queue: {queue}")

    with Connection(URL) as conn:
        logging.debug("Established connection")
        producer = conn.Producer(serializer="json")
        counter = TaskCounter()
        for task in counter.stream(store.load_tasks(task_name)):
            logging.debug("Publishing task ID: %s", task.id)
            producer.publish(
                task.body,
                exchange=_exchange,
                routing_key=routing_key,
                declare=[queue],
                headers=task.headers,
            )
            store.delete(task)
        counter.display()


def drain(queue: Queue, store: TaskStore) -> None:
    logging.info(f"Draining queue: {queue}")

    def callback(_, message: Message):
        task = StoredTask.from_message(message)
        logging.debug("Received task: %s", task)
        store.save(task)
        message.ack()

    with Connection(URL) as conn:
        with conn.Consumer(queue, callbacks=[callback]) as consumer:
            consumer.qos(prefetch_count=CONSUMER_PREFETCH_COUNT)
            try:
                while True:
                    conn.drain_events(timeout=1)
            except socket.timeout:
                pass
            except KeyboardInterrupt:
                consumer.recover(requeue=True)
                raise
    list_(queue, store, counts=True)


def list_(
    queue: Queue,
    store: TaskStore,
    counts=False,
    limit: Optional[int] = None,
    task_name: Optional[str] = None,
) -> None:
    stream = store.load_tasks(task_name)
    if limit:
        stream = islice(stream, limit)
    if counts:
        counter = TaskCounter()
        list(counter.stream(stream))
        counter.display()
    else:
        items = []
        for task in stream:
            items.append((task.id, task.task, task.argsrepr, task.kwargsrepr))
        if items:
            termtables.print(items, header=["ID", "Task", "Args", "Kwargs"])


def drain_command(queue: Queue, store: TaskStore, args: argparse.Namespace) -> None:
    drain(queue, store)


def fill_command(queue: Queue, store: TaskStore, args: argparse.Namespace) -> None:
    fill(queue, store, args.routing_key, task_name=args.task)


def list_command(queue: Queue, store: TaskStore, args: argparse.Namespace) -> None:
    list_(queue, store, counts=args.counts, task_name=args.task, limit=args.limit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q",
        "--queue",
        default="celery",
        help="Queue to operate on. Defaults to 'celery'",
    )
    parser.add_argument(
        "-k", "--routing-key", default="celery", help="Message routing key"
    )
    parser.add_argument(
        "-s",
        "--store",
        choices=("file", "sqlite"),
        default="sqlite",
        help="Task storage option",
    )
    parser.add_argument("-L", "--log-level", default=DEFAULT_LOG_LEVEL)
    subparsers = parser.add_subparsers()

    drain_parser = subparsers.add_parser("drain", help="Drain tasks from the queue")
    # drain_parser.add_argument(
    #     "-l", "--limit", help="Limit number of tasks retrieved", type=int
    # )
    drain_parser.set_defaults(func=drain_command)

    fill_parser = subparsers.add_parser("fill", help="Put tasks back on the queue")
    fill_parser.set_defaults(func=fill_command)
    fill_parser.add_argument(
        "-t", "--task", help="Optionally populate the queue with only this type of task"
    )

    list_parser = subparsers.add_parser("list", help="Show retrieved tasks")
    list_parser.add_argument(
        "-c", "--counts", help="Display counts for each task type", action="store_true"
    )
    list_parser.add_argument(
        "-l", "--limit", help="Limit number of rows shown.", type=int
    )
    list_parser.add_argument("-t", "--task", help="List tasks with this name")
    list_parser.set_defaults(func=list_command)

    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper(), DEFAULT_LOG_LEVEL)

    logging.basicConfig(level=log_level)

    queue = Queue(args.queue, exchange=_exchange, routing_key=args.routing_key)

    store: TaskStore
    if args.store == "sqlite":
        store = SqliteTaskStore("tasks.sqlite")
    else:
        store = FileTaskStore("tasks")

    try:
        args.func(queue, store, args)
    except AttributeError:
        # Didn't pass a subcommand
        parser.print_help()
