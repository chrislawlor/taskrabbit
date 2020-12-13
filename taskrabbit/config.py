import configparser

from dataclasses import dataclass
from pathlib import Path


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
            f"{self.host}:{self.port}/{self.vhost}"
        )


class StoreConfig:
    pass


@dataclass
class Config:
    store: StoreConfig
    log_level: str
    rabbitmq: RabbitMQConfig


@dataclass(frozen=True)
class SqliteConfig(StoreConfig):
    db: str
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


STORE_CONFIG_MAP = {"sqlite": SqliteConfig, "postgres": PostgresConfig}


def _update_config(config, options):
    for k, v in config.items():
        if k in options:
            if hasattr(v, "items"):
                _update_config(config[k], options[k])
            else:
                config[k] = options[k]


def load_config(*paths: Path, **opts):
    config_paths = list(filter(lambda p: p.exists(), paths))

    cfg = configparser.ConfigParser()

    for path in config_paths:
        cfg.read(path)

    _update_config(cfg, opts)

    store_type = cfg["taskrabbit"]["store"]
    del cfg["taskrabbit"]["store"]
    store_cls = STORE_CONFIG_MAP[store_type]
    store_cfg = store_cls(**cfg[store_type])
    rabbit_cfg = RabbitMQConfig(**cfg["rabbitmq"])
    cfg = Config(rabbitmq=rabbit_cfg, store=store_cfg, **cfg["taskrabbit"])
    return cfg
