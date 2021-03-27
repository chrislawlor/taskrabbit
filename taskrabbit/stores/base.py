import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from kombu import Message


@dataclass
class StoredTask:
    headers: Dict[str, Any]
    body: Any
    routing_key: str
    # args: List[Any]
    # kwargs: Dict[str, Any]

    def json(self, indent=2):
        return json.dumps(
            {
                "headers": self.headers,
                "body": self.body,
                "routing_key": self.routing_key,
            },
            indent=indent,
        )

    @classmethod
    def from_string(cls, string):
        data = json.loads(string)
        return cls(**data)

    @classmethod
    def from_message(cls, message: Message):
        # Kombu docs say message.body is a str, but it's really a memoryview,
        # which is not JSON serializable
        return cls(
            body=message.decode(),
            headers=message.headers,
            routing_key=message.delivery_info["routing_key"],
            # args=message.payload[0],
            # kwargs=message.payload[1],
        )

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
    """
    Abstract base class for storing tasks.
    """

    @abstractmethod
    def save(self, task: StoredTask):
        ...

    def bulk_save(self, tasks: Iterable[StoredTask]):
        for task in tasks:
            self.save(task)

    @abstractmethod
    def load_tasks(self, task_name=Optional[str]) -> Iterable[StoredTask]:
        ...

    @abstractmethod
    def delete(self, task: StoredTask):
        ...

    # Optional functionality

    def dedupe(self) -> int:
        """
        Remove duplicate tasks from the store.

        Returns the number of tasks removed.
        """
        raise NotImplementedError()
