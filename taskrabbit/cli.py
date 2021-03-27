import logging
from enum import Enum
from pathlib import Path
from typing import Optional

import typer

from taskrabbit import __version__

from .config import Config, load_config, ConfigurationError
from .operations import drain, fill, list_
from .stores.base import TaskStore
from .utils import pluralize, green, red


HOME_CONFIG_PATH = Path.home() / ".taskrabbit.ini"

app = typer.Typer()
store_app = typer.Typer()
app.add_typer(store_app, name="store")


class LogLevels(str, Enum):
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


def init_store(cfg: Config) -> TaskStore:
    if cfg.store.name == "sqlite":
        from .stores.sqlite import SqliteTaskStore

        return SqliteTaskStore(cfg.store)
    if cfg.store.name == "postgres":
        from .stores.postgres import PostgresTaskStore

        return PostgresTaskStore(cfg.store)
    from .stores.file import FileTaskStore

    return FileTaskStore(cfg.store)


@store_app.command("dedupe")
def de_duplicate(ctx: typer.Context):
    """
    Remove duplicate tasks.
    """
    confirmed = typer.confirm(red("This is a destructive operation. Continue?"))
    if not confirmed:
        raise typer.Abort()
    cfg = ctx.meta["config"]
    store = init_store(cfg)
    try:
        count = store.dedupe()
    except NotImplementedError:
        typer.echo(
            red(f"{store.__class__.__name__} does not support task de-duplication."),
        )
        raise typer.Exit(code=1)
    # count_display = typer.style(str(count), fg=typer.colors.GREEN)
    typer.echo(
        f"Removed {green(count)} duplicate task{pluralize(count)} from the store."
    )


@app.command("drain")
def drain_command(
    ctx: typer.Context,
    queue: str = typer.Argument(..., help="Queue to drain tasks from."),
) -> None:
    """
    Drain tasks from the queue.
    """
    cfg = ctx.meta["config"]
    store = init_store(cfg)
    drain(cfg, queue, store)
    print("Stored tasks:")
    list_(store, counts=True)


@app.command("fill")
def fill_command(
    ctx: typer.Context,
    exchange: str = typer.Argument("", help="Tasks will be published to this exchange"),
    task_name: Optional[str] = typer.Option(
        None, help="Only publish tasks with this name"
    ),
    delete: bool = typer.Option(True, help="Delete tasks from store after publishing."),
    confirm: bool = typer.Option(True, help="Confirm exchange before publishing"),
) -> None:
    """
    Publish tasks to an exchange.
    """

    # Confirm exhange
    exchange_display = exchange if exchange else "default"
    if confirm:
        confirmed = typer.confirm(f"Publish tasks to the {exchange_display} exchange?")
        if not confirmed:
            raise typer.Abort()
    cfg = ctx.meta["config"]
    store = init_store(cfg)
    fill(cfg, exchange, store, task_name, delete)


@store_app.command("list")
def list_command(
    ctx: typer.Context,
    counts: bool = typer.Option(
        False, "--counts", "-c", help="Only show task counts, by name"
    ),
    task: Optional[str] = typer.Option(None, help="List only tasks with this name."),
    limit: Optional[int] = typer.Option(None, help="Limit number of tasks shown"),
) -> None:
    """
    Show retrieved tasks.
    """
    store = init_store(ctx.meta["config"])
    list_(store, counts=counts, task_name=task, limit=limit)


def show_version(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit()


def check_config(value) -> Optional[Path]:
    if value is None:
        path = Path("taskrabbit.ini")
        if path.exists():
            return path
    else:
        path = value.absolute()
        if not path.exists():
            raise typer.BadParameter(f"Config file does not exist at {path}")
        return value
    return None


@app.callback()
def main(
    ctx: typer.Context,
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        exists=True,
        readable=True,
        resolve_path=True,
        callback=check_config,
    ),
    log_level: str = typer.Option(LogLevels.info, case_sensitive=False),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=show_version,
        help="Display the program version.",
        is_eager=True,
    ),
):
    """
    Remove and restore Celery tasks from RabbitMQ.
    """
    config_paths = [HOME_CONFIG_PATH]
    if config is not None:
        config_paths.append(config)
    try:
        cfg = load_config(*config_paths, taskrabbit={"log_level": log_level.upper()})
        log_level = getattr(logging, cfg.log_level)
        logging.basicConfig(level=log_level)
        logging.debug("Loaded configuration: %s", cfg)

        ctx.meta["config"] = cfg
    except ConfigurationError as exc:
        raise typer.BadParameter(str(exc)) from exc
