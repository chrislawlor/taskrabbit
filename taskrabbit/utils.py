import typer


def pluralize(count: int):
    return "" if count == 1 else "s"


def green(obj):
    return typer.style(str(obj), fg=typer.colors.GREEN)


def red(obj):
    return typer.style(str(obj), fg=typer.colors.RED)
