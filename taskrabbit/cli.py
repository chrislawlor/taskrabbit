import argparse
import logging
from taskrabbit.stores.postgres import PostgresTaskStore

from . import config
from .operations import drain, fill, list_
from .stores.base import TaskStore


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
    drain(args.exchange, args.queue, store)
    print("Stored tasks:")
    list_(store, counts=True)


def fill_command(cfg: config.Config, args: argparse.Namespace) -> None:
    store = init_store(cfg)
    fill(args.exchange, store, task_name=args.task)


def list_command(cfg: config.Config, args: argparse.Namespace) -> None:
    store = init_store(cfg)
    list_(store, counts=args.counts, task_name=args.task, limit=args.limit)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="taskrabbit.ini")
    parser.add_argument("-x", "--exchange", default="celery")
    parser.add_argument(
        "-q",
        "--queue",
        default="celery",
        help="Queue to operate on. Defaults to 'celery'",
    )
    parser.add_argument("-L", "--log-level", default=config.DEFAULT_LOG_LEVEL)
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

    cfg = config.load_config(args.config, taskrabbit={"log_level": args.log_level})

    log_level = getattr(logging, cfg.log_level, config.DEFAULT_LOG_LEVEL)

    logging.basicConfig(level=log_level)

    try:
        args.func(cfg, args)
    except AttributeError:
        # Didn't pass a subcommand
        parser.print_help()
