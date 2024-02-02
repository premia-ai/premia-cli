import re
import click
from datetime import datetime
from premia.db import migration


def execute_completion(completion: str):
    conn = migration.connect()
    sql_fence_pattern = r"```sql([\s\S]*?)```"
    sql_commands = re.findall(sql_fence_pattern, completion, re.DOTALL)

    if len(sql_commands) == 0:
        return

    if click.confirm("Do you want to execute the suggested SQL command?"):
        try:
            relation = conn.sql(sql_commands[0].strip())
            relation.show()
            if click.confirm(
                "Do you want to store this result for further questions?"
            ):
                view_name = f"ai_response_{datetime.now().strftime('%Y_%m_%dT%H_%M_%S')}"
                relation.create_view(view_name)
                click.echo(
                    f"The result has been stored as '{view_name}'. You can refer to it in your queries."
                )
        except Exception as e:
            click.secho(
                f"""
The following error was raised while executing the SQL command:
{e} 
""",
                fg="red",
            )
