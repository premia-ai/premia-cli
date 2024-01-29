import click
from ai import model
from db import internals
from utils import config
import wizard.db_cmd


@click.version_option("0.0.1", prog_name="premia")
@click.group()
def cli():
    """Cli to setup and interact with financial data infrastructure"""
    pass


@cli.group()
def ai():
    """Use an open source LLM to interact with your financial data"""
    pass


@ai.command("init")
@click.option("-f", "--force", default=False, is_flag=True)
@click.option(
    "-n",
    "--name",
    help="The name of a model's huggingface repo (including the username)",
)
@click.option(
    "-f", "--file", help="The file name inside the repo you want to download"
)
def ai_init(force: bool, name: str, file: str):
    """Initialize an open source LLM on your machine"""

    if (name and not file) or (file and not name):
        click.secho(
            "Error: You need to define both a name and a file",
            err=True,
            fg="red",
        )
        raise click.Abort()

    model.init(force=force, model_name=name, model_file=file)


@ai.command()
@click.argument("prompt")
@click.option(
    "-v",
    "--verbose",
    default=False,
    is_flag=True,
    help="Print the execution of the LLM",
)
def query(prompt: str, verbose: bool):
    """Turn a natural language query into an SQL command with the help of an open source LLM"""
    model.create_completion(prompt, verbose=verbose)


@cli.group()
def db():
    """Setup and inspect your database."""
    pass


@db.command()
def inspect():
    try:
        db_schema = internals.inspect()
        click.echo(db_schema)
    except ValueError as e:
        click.secho(e, fg="red")
        raise click.Abort()


@db.command("init")
def db_init():
    """Initialize a financial database"""
    config.setup_config_dir()

    try:
        wizard.db_cmd.setup()
    except Exception as e:
        click.secho(e, fg="red")
        raise click.Abort()

    if not click.confirm("Do you want to seed the db?"):
        return

    try:
        wizard.db_cmd.seed()
    except Exception as e:
        click.secho(e, fg="red")
        raise click.Abort()


@db.command("import")
def db_import():
    try:
        wizard.db_cmd.seed()
    except Exception as e:
        click.secho(e, fg="red")
        raise click.Abort()


if __name__ == "__main__":
    cli()
