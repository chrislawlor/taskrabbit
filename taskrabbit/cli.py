import argparse
import logging
import sys
from pathlib import Path

from . import config
from .operations import drain, fill, list_
from .stores.base import TaskStore

HOME_CONFIG_PATH = Path.home() / ".taskrabbit.ini"


def init_store(cfg: config.Config) -> TaskStore:
    if cfg.store.name == "sqlite":
        from .stores.sqlite import SqliteTaskStore

        return SqliteTaskStore(cfg.store)
    if cfg.store.name == "postgres":
        from .stores.postgres import PostgresTaskStore

        return PostgresTaskStore(cfg.store)
    from .stores.file import FileTaskStore

    return FileTaskStore(cfg.store)


def drain_command(cfg: config.Config, args: argparse.Namespace) -> None:
    store = init_store(cfg)
    drain(cfg, args.queue, store)
    print("Stored tasks:")
    list_(store, counts=True)


def fill_command(cfg: config.Config, args: argparse.Namespace) -> None:
    store = init_store(cfg)
    fill(cfg, args.exchange, store, task_name=args.task)


def list_command(cfg: config.Config, args: argparse.Namespace) -> None:
    store = init_store(cfg)
    list_(store, counts=args.counts, task_name=args.task, limit=args.limit)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="taskrabbit.ini")

    parser.add_argument("-L", "--log-level", default=config.DEFAULT_LOG_LEVEL)

    subparsers = parser.add_subparsers(help="sub-command help")

    drain_parser = subparsers.add_parser("drain", help="Drain tasks from the queue")
    drain_parser.add_argument("queue", help="Queue to drain tasks from.")
    # drain_parser.add_argument(
    #     "-l", "--limit", help="Limit number of tasks retrieved", type=int
    # )
    drain_parser.set_defaults(func=drain_command)

    fill_parser = subparsers.add_parser("fill", help="Publish tasks to an exchange")
    fill_parser.add_argument("exchange", help="Publish tasks to this exchange")
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

    cfg = config.load_config(
        HOME_CONFIG_PATH,
        Path(args.config).absolute(),
        taskrabbit={"log_level": args.log_level.upper()},
    )

    log_level = getattr(logging, cfg.log_level)

    logging.basicConfig(level=log_level)
    logging.debug("Loaded configuration: %s", cfg)

    if not hasattr(args, "func"):
        # Didn't pass a subcommand
        parser.print_help()
        sys.exit(1)

    try:
        args.func(cfg, args)
    except Exception as e:
        logging.error(str(e))
        sys.exit(2)
