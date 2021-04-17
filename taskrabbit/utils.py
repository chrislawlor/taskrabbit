import typer
from contextlib import contextmanager
from importlib import import_module

from halo import Halo

SPINNER = "dots12"


def pluralize(count: int):
    return "" if count == 1 else "s"


def green(obj):
    return typer.style(str(obj), fg=typer.colors.GREEN)


def red(obj):
    return typer.style(str(obj), fg=typer.colors.RED)


# From django.utils.module_loading
def import_string(dotted_path):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import failed.
    """
    try:
        module_path, class_name = dotted_path.rsplit(".", 1)
    except ValueError as err:
        raise ImportError("%s doesn't look like a module path" % dotted_path) from err

    module = import_module(module_path)

    try:
        return getattr(module, class_name)
    except AttributeError as err:
        raise ImportError(
            'Module "%s" does not define a "%s" attribute/class'
            % (module_path, class_name)
        ) from err


@contextmanager
def spinner(text: str):
    with Halo(text=text, spinner=SPINNER):
        yield
