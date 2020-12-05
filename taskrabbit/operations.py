import logging
import socket
from collections import Counter
from itertools import islice
from typing import Optional, Iterable
import termtables
from kombu import Connection, Message, Queue

from . import config
from .stores.base import StoredTask, TaskStore


class TaskCounter(Counter):
    def stream(self, tasks: Iterable[StoredTask]):
        for task in tasks:
            self.update([task.task])
            yield task

    def display(self):
        if self:
            termtables.print(self.most_common(), header=["Task", "Count"])


def fill(exchange: str, store: TaskStore, task_name: Optional[str] = None) -> None:
    # Uncomment this to fill tasks to a different queue
    # queue = Queue("fill", exchange=_exchange, routing_key=ROUTING_KEY)
    # logging.info(f"Filling queue: {queue}")

    with Connection(config.URL) as conn:
        logging.debug("Established connection")
        producer = conn.Producer(serializer="json")
        counter = TaskCounter()
        for task in counter.stream(store.load_tasks(task_name)):
            logging.debug("Publishing task ID: %s", task.id)
            producer.publish(
                task.body,
                exchange=exchange,
                routing_key=task.routing_key,
                headers=task.headers,
            )
            store.delete(task)
        counter.display()


def drain(exchange_name: str, queue_name: str, store: TaskStore) -> None:
    queue = Queue(queue_name, exchange=exchange_name)
    logging.info(f"Draining queue: {queue}")

    def callback(_, message: Message):
        task = StoredTask.from_message(message)
        logging.debug("Received task: %s", task)
        store.save(task)
        message.ack()

    with Connection(config.URL) as conn:
        with conn.Consumer(queue, callbacks=[callback]) as consumer:
            consumer.qos(prefetch_count=config.CONSUMER_PREFETCH_COUNT)
            try:
                while True:
                    conn.drain_events(timeout=1)
            except socket.timeout:
                pass
            except KeyboardInterrupt:
                consumer.recover(requeue=True)
                raise


def list_(
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
