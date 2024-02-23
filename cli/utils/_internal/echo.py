import json
from typing import Iterator
import yaml
import pandas as pd
import click
from .loader import Loader


def echo_list(
    values: list[str], as_json=False, as_csv=False, name: str | None = None
) -> None:
    """
    Print a list to stdout.
    """
    if as_json:
        if name:
            result = json.dumps({name: values}, indent=4)
        else:
            result = json.dumps(values, indent=4)
    elif as_csv:
        header = name + "\n" if name else ""
        rows = "\n".join(values)
        result = f"{header}{rows}"
    else:
        if name:
            result = yaml.dump({name: values}).strip()
        else:
            result = yaml.dump(values).strip()

    click.echo(result)


def echo_df(df: pd.DataFrame, rows=10, as_json=False, as_csv=False) -> None:
    """
    Print a DataFrame to stdout. If rows is -1 it will print the whole DataFrame to stdout, else just the first n rows.
    """
    if rows != -1:
        df = df.head(rows)

    if as_json:
        result = df.to_json(orient="records", indent=4)
    elif as_csv:
        result = df.to_csv(index=False)
    else:
        result = df.to_markdown(tablefmt="rounded_outline")

    click.echo(result)


def echo_iter(iterator: Iterator[str]) -> None:
    loader = Loader()
    loader.start()
    for value in iterator:
        loader.stop()
        click.echo(value, nl=False)
    click.echo()
