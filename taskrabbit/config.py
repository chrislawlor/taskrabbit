import os
from dataclasses import dataclass
from pathlib import Path

from config import ConfigurationSet, config_from_env, config_from_dict, config_from_path

USERNAME = "guest"
PASSWORD = "guest"
HOST = "localhost"
PORT = 5672
VHOST = "/"
# EXCHANGE = "taskrabbit"
DEFAULT_LOG_LEVEL = "INFO"

# Sets kombu Consumer prefetch count
# See https://docs.celeryproject.org/projects/kombu/en/stable/userguide/consumers.html#reference  # noqa
CONSUMER_PREFETCH_COUNT = 500

URL = f"amqp://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{VHOST}"


DEFAULTS = {
    "taskrabbit": {"store": "sqlite", "log_level": "INFO"},
    "rabbitmq": {
        "username": "guest",
        "password": "guest",
        "host": "localhost",
        "port": "5672",
        "vhost": "/",
    },
    "sqlite": {
        "db": "tasks.sqlite",
    },
}

CONFIG_PATHS = [
    Path.home() / ".taskrabbit.ini",
    Path("taskrabbit.ini"),
]


@dataclass
class RabbitMQConfig:
    username: str
    password: str
    host: str
    port: str = "5672"
    vhost: str = "/"

    def url(self):
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/{self.vhost}"


class StoreConfig:
    pass


@dataclass
class Config:
    store: StoreConfig
    log_level: str
    rabbitmq: RabbitMQConfig


@dataclass
class SqliteConfig(StoreConfig):
    name = "sqlite"
    db: str


@dataclass
class PostgresConfig(StoreConfig):
    name = "postgres"
    username: str
    password: str
    host: str
    port: str
    db: str

    def get_dsn(self):
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.db}"


@dataclass
class FileConfig(StoreConfig):
    name = "file"
    directory = "tasks"


STORE_CONFIG_MAP = {
    "sqlite": SqliteConfig,
    "postgres": PostgresConfig,
}


def load_config(config_file, **opts):
    config_paths = list(
        filter(
            lambda p: p.exists(), [Path(config_file), Path.home() / ".taskrabbit.ini"]
        )
    )

    config_set = ConfigurationSet(
        config_from_dict(opts),
        *map(config_from_path, config_paths),
        config_from_dict(DEFAULTS),
    )
    store_type = config_set.pop("taskrabbit.store")
    store_cls = STORE_CONFIG_MAP[store_type]
    store_cfg = store_cls(**config_set.pop(store_type))
    rabbit_cfg = RabbitMQConfig(**config_set.pop("rabbitmq"))
    return Config(rabbitmq=rabbit_cfg, store=store_cfg, **config_set["taskrabbit"])
