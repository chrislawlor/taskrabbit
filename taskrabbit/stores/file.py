import os
from pathlib import Path
from typing import Iterable, Optional

from taskrabbit.config import FileConfig
from .base import TaskStore, StoredTask


class FileTaskStore(TaskStore):
    def __init__(self, cfg: FileConfig):
        self.path = Path() / cfg.directory
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
