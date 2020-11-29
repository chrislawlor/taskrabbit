import argparse
import json
import logging
import os
from re import A
import socket
import sqlite3
import termtables
from abc import ABC, abstractmethod
from collections import Counter, deque
from dataclasses import dataclass
from itertools import islice
from typing import Any, Counter as CounterType, Dict, Iterable, List, Optional
from uuid import uuid4

from kombu import Connection, Exchange, Message, Queue

USERNAME = "guest"
PASSWORD = "guest"
HOST = "rabbit"
PORT = 5672
VHOST = "/"
EXCHANGE = "default"
QUEUE = "celery"
ROUTING_KEY = "celery"
DEFAULT_LOG_LEVEL = "DEBUG"

# Sets kombu Consumer prefetch count
# See https://docs.celeryproject.org/projects/kombu/en/stable/userguide/consumers.html#reference
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


class MessageStore(ABC):
    @abstractmethod
    def save(self, task: StoredTask):
        ...

    @abstractmethod
    def load_messages(self, task_name=Optional[str]) -> Iterable[StoredTask]:
        ...

    @abstractmethod
    def delete(self, task: StoredTask):
        ...

    def callback(self, _, message):
        task = StoredTask.from_message(message)
        logging.debug("Retrieved task: %s", task)
        self.save(task)
        message.ack()


class FileMessageStore(MessageStore):
    def __init__(self, directory):
        self.directory = directory

    def save(self, task: StoredTask):
        with open(os.path.join(self.directory, task.id), "w") as f:
            f.write(task.json())

    def load_messages(self, task_name=Optional[str]) -> Iterable[StoredTask]:
        for filename in os.scandir(self.directory):
            with open(filename) as f:
                data = f.read()
                task = StoredTask.from_string(data)
                if task_name is None or task.task == task_name:
                    yield task

    def delete(self, task: StoredTask):
        try:
            os.remove(os.path.join(self.directory, task.id))
        except FileNotFoundError:
            pass


class SqliteMessageStore(MessageStore):
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

    def load_messages(self, task_name: Optional[str] = None) -> Iterable[StoredTask]:
        if task_name is None:
            cursor = self.execute("SELECT * FROM tasks")
        else:
            cursor = self.execute("SELECT * FROM tasks WHERE task=?", (task_name,))
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


def fill(queue: Queue, store: MessageStore, args: argparse.Namespace) -> None:
    # Uncomment this to fill tasks to a different queue
    # queue = Queue("fill", exchange=_exchange, routing_key=ROUTING_KEY)
    logging.info(f"Filling queue: {queue}")

    with Connection(URL) as conn:
        logging.debug("Established connection")
        producer = conn.Producer(serializer="json")
        counter = TaskCounter()
        for message in counter.stream(store.load_messages(task_name=args.task)):
            logging.debug("Publishing message ID: %s", message.id)
            producer.publish(
                message.body,
                exchange=_exchange,
                routing_key=ROUTING_KEY,
                declare=[queue],
                headers=message.headers,
            )
            store.delete(message)
        counter.display()


def drain(queue: Queue, store: MessageStore, args: argparse.Namespace) -> None:
    logging.info(f"Draining queue: {queue}")
    # if args.limit:
    #     store.set_limit(args.limit)
    with Connection(URL) as conn:
        with conn.Consumer(queue, callbacks=[store.callback]) as consumer:
            consumer.qos(prefetch_count=CONSUMER_PREFETCH_COUNT)
            try:
                while True:
                    conn.drain_events(timeout=1)
            except socket.timeout:
                pass
            except KeyboardInterrupt:
                consumer.recover(requeue=True)
                raise


def list_(queue: Queue, store: MessageStore, args: argparse.Namespace) -> None:
    stream = store.load_messages()
    if args.limit:
        stream = islice(stream, args.limit)
    if args.counts:
        counter = TaskCounter()
        list(counter.stream(stream))
        counter.display()
    else:
        items = []
        for task in stream:
            items.append((task.id, task.task, task.argsrepr, task.kwargsrepr))
        if items:
            termtables.print(items, header=["ID", "Task", "Args", "Kwargs"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q",
        "--queue",
        default="celery",
        help="Queue to operate on. Defaults to 'celery'",
    )
    parser.add_argument(
        "-s",
        "--store",
        choices=("file", "sqlite"),
        default="sqlite",
        help="Message storage option",
    )
    parser.add_argument("-L", "--log-level", default=DEFAULT_LOG_LEVEL)
    subparsers = parser.add_subparsers()

    drain_parser = subparsers.add_parser("drain", help="Drain messages from the queue")
    drain_parser.add_argument(
        "-l", "--limit", help="Limit number of tasks retrieved", type=int
    )
    drain_parser.set_defaults(func=drain)

    fill_parser = subparsers.add_parser("fill", help="Put messages back on the queue")
    fill_parser.set_defaults(func=fill)
    fill_parser.add_argument(
        "-t",
        "--task",
        required=False,
        help="Optionally populate the queue with only this type of task",
    )

    list_parser = subparsers.add_parser("list", help="Show retrieved messages")
    list_parser.add_argument("-c", "--counts", help="Display counts for each task type")
    list_parser.add_argument(
        "-l", "--limit", help="Limit number of rows shown.", type=int
    )
    list_parser.set_defaults(func=list_)

    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper(), DEFAULT_LOG_LEVEL)

    logging.basicConfig(level=log_level)

    queue = Queue(args.queue, exchange=_exchange, routing_key=ROUTING_KEY)

    store: MessageStore
    if args.store == "sqlite":
        store = SqliteMessageStore("tasks.sqlite")
    else:
        store = FileMessageStore("messages")

    args.func(queue, store, args)
