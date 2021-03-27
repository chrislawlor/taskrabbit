import logging
import socket
from collections import Counter
from itertools import islice
from typing import List, Optional, Iterable
import termtables
from kombu import Connection, Exchange, Message, Queue
from amqp.exceptions import NotFound as AMQPNotFound

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


def fill(
    cfg: config.Config,
    exchange_name: str,
    store: TaskStore,
    task_name: Optional[str] = None,
    delete: bool = True,
) -> None:
    # Don't publish to system exchanges
    if exchange_name.startswith("amq"):
        raise ValueError(f"Cannot publish to system exchange: {exchange_name}")

    with Connection(cfg.rabbitmq.url()) as conn:
        with conn.channel() as channel:
            try:
                counter = TaskCounter()
                # Passively declare the exchange so we can fail if it doesn't
                # already exist.
                exchange = Exchange(exchange_name, channel=channel, passive=True)
                logging.debug("Established connection")
                producer = conn.Producer(
                    exchange=exchange, channel=channel, serializer="json"
                )
                for task in counter.stream(store.load_tasks(task_name)):
                    logging.debug("Publishing task ID: %s", task.id)
                    producer.publish(
                        task.body,
                        exchange=exchange,
                        routing_key=task.routing_key,
                        headers=task.headers,
                    )
                    if delete:
                        store.delete(task)
                counter.display()
            except AMQPNotFound as ex:
                logging.error(str(ex))


def drain(cfg: config.Config, queue_name: str, store: TaskStore) -> None:
    queue = Queue(queue_name)
    logging.info(f"Draining queue: {queue}")

    requeue: List[Message] = []

    def callback(_, message: Message):
        nonlocal requeue
        task = StoredTask.from_message(message)
        logging.debug("Received task: %s", task)
        try:
            store.save(task)
            message.ack()
        except Exception:
            requeue.append(message)

    # TODO: Safer persistence for messages that need to be requeued.
    with Connection(cfg.rabbitmq.url()) as conn:
        try:
            with conn.Consumer(queue, callbacks=[callback]) as consumer:
                consumer.qos(
                    prefetch_count=config.RabbitMQConfig.consumer_prefetch_count
                )
                try:
                    while True:
                        conn.drain_events(timeout=1)
                except socket.timeout:
                    pass
                except KeyboardInterrupt:
                    consumer.recover(requeue=True)
                    raise
        finally:
            if requeue:
                for message in requeue:
                    message.requeue()


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
            items.append(
                (task.id, task.task, task.argsrepr, task.kwargsrepr, task.routing_key)
            )
        if items:
            termtables.print(
                items, header=["ID", "Task", "Args", "Kwargs", "Routing Key"]
            )
