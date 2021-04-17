import configparser

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from taskrabbit.utils import import_string
from taskrabbit.stores.base import TaskStore


DEFAULT_LOG_LEVEL = "INFO"

# Sets kombu Consumer prefetch count
# See https://docs.celeryproject.org/projects/kombu/en/stable/userguide/consumers.html#reference  # noqa
DEFAULT_CONSUMER_PREFETCH_COUNT = 100


DEFAULTS = {
    "taskrabbit": {"store": "sqlite", "log_level": "INFO"},
    "rabbitmq": {
        "username": "guest",
        "password": "guest",
        "host": "localhost",
        "port": "5672",
        "vhost": "/",
    },
    "sqlite": {"db": "tasks.sqlite"},
}

CONFIG_PATHS = [Path.home() / ".taskrabbit.ini", Path("taskrabbit.ini")]


class ConfigurationError(Exception):
    pass


@dataclass(frozen=True)
class RabbitMQConfig:
    username: str
    password: str
    host: str
    port: str = "5672"
    vhost: str = "/"
    consumer_prefetch_count: int = DEFAULT_CONSUMER_PREFETCH_COUNT

    def url(self):
        return (
            f"amqp://{self.username}:{self.password}@"
            f"{self.host}:{self.port}{self.vhost}"
        )

    def __post_init__(self):
        if not self.vhost.startswith("/"):
            raise ValueError(f"{self.__class__.__name__}.vhost must have a leading /")


class StoreConfig:
    name: str


@dataclass
class Config:
    store_config: StoreConfig
    log_level: str
    rabbitmq: RabbitMQConfig
    store_class: TaskStore

    @classmethod
    def from_config_dict(cls, cfg: Mapping):
        store_path = cfg["taskrabbit"]["store"]
        del cfg["taskrabbit"]["store"]
        store_cls = import_string(store_path)
        store_config_cls = store_cls.config_class
        if "store" in cfg:
            store_cfg = store_config_cls(**cfg["store"])
        else:
            store_cfg = store_config_cls()
        rabbit_cfg = RabbitMQConfig(**cfg["rabbitmq"])
        config = cls(
            rabbitmq=rabbit_cfg,
            store_config=store_cfg,
            store_class=store_cls,
            **cfg["taskrabbit"],
        )
        return config

    def init_store(self):
        return self.store_class(self.store_config)


@dataclass(frozen=True)
class SqliteConfig(StoreConfig):
    db: str = "tasks.sqlite"
    name: str = "sqlite"


@dataclass(frozen=True)
class PostgresConfig(StoreConfig):
    username: str
    password: str
    host: str
    port: str
    db: str
    name: str = "postgres"

    def get_dsn(self):
        return (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.db}"
        )


@dataclass(frozen=True)
class FileConfig(StoreConfig):
    name = "file"
    directory = "tasks"


def _update_config(config, options):
    """
    Recursively overwrite keys in `config` with values from `options`.
    """
    for k, v in config.items():
        if k in options:
            if hasattr(v, "items"):
                _update_config(config[k], options[k])
            else:
                config[k] = options[k]


def merge_config_files_and_options(*paths: Path, **opts) -> configparser.ConfigParser:
    """
    Load + merge multiple config paths, overriding values with
    kwarg options.

    Will raise ConfigurationError if at least one path is not found.
    """
    config_paths = list(filter(lambda p: p.exists(), paths))
    if not config_paths:
        raise ConfigurationError("No config file found.")

    cfg = configparser.ConfigParser()

    for path in config_paths:
        cfg.read(path)

    _update_config(cfg, opts)

    return cfg
