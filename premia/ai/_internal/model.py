import re
from typing import Iterator, cast
from datetime import datetime
from dataclasses import dataclass
import pandas as pd
from llama_cpp import (
    CreateCompletionResponse,
    CreateCompletionStreamResponse,
    Llama,
)
from openai import OpenAI
from premia import config, db

LOCAL_MESSAGES_TEMPLATE = """
[INST]
{system_prompt}
[/INST]
[USER]
{user_prompt}
[/USER]    
</s> """

LOCAL_SYSTEM_PROMPT_QUERY_TEMPLATE = """
You are a text-to-SQL assistant.

You are given a specification for a database query starting with "[USER]" and ending with "[/USER]".

DuckDB SQL-database schema:
```sql
{db_schema}
```

Write a single SQL command to fulfill the specification.
Only include tables, views and columns specified in the SQL-database schema.
"""

REMOTE_SYSTEM_PROMPT_QUERY_TEMPLATE = """
DuckDB SQL-database schema:
```sql
{db_schema}
```
You are a text-to-SQL assistant.

You are given a specification for a database query from the user.

Write a single SQL command to fulfill the specification.
Only include tables, views and columns specified in the SQL-database schema.
"""


LOCAL_SYSTEM_PROMPT_ASK_TEMPLATE = """
You are a financial data assistant.

You are given a question from a user starting with "[USER]" and ending with "[/USER]".

Here, the user's SQL-database schema:
```sql
{db_schema}
```

Answer the user's question in a step by step manner.
When possible make use of the information you have about the user.
"""

REMOTE_SYSTEM_PROMPT_ASK_TEMPLATE = """
You are a financial data assistant.

Here, the user's SQL-database schema:
```sql
{db_schema}
```

Answer the user's question in a step by step manner.
When possible make use of the information you have about the user.
"""


def get_local_prompt(user_prompt: str) -> str:
    return LOCAL_SYSTEM_PROMPT_QUERY_TEMPLATE.format(
        db_schema=db.schema(), user_prompt=user_prompt
    )


def get_local_model(verbose=False) -> Llama:
    local_ai_config = config.get_ai_local()
    return Llama(
        model_path=local_ai_config["model_path"],
        n_ctx=8000,
        n_threads=7,
        n_gpu_layers=0,
        verbose=verbose,
    )


def create_local_completion_iter(
    user_prompt: str, system_prompt: str, verbose: bool
) -> Iterator[str]:
    model = get_local_model(verbose)
    completion = model(
        LOCAL_MESSAGES_TEMPLATE.format(
            system_prompt=system_prompt, user_prompt=user_prompt
        ),
        max_tokens=2048,
        top_k=0,
        echo=verbose,
        stream=True,
    )

    completion = cast(Iterator[CreateCompletionStreamResponse], completion)
    for chunk in completion:
        yield chunk["choices"][0]["text"]


def create_local_completion_str(
    user_prompt: str,
    system_prompt: str,
    verbose: bool,
    temperature: float = 0.8,
) -> str:
    model = get_local_model(verbose)
    completion = model(
        get_local_prompt(user_prompt),
        max_tokens=2048,
        top_k=0,
        echo=verbose,
        stream=False,
        temperature=temperature,
    )

    completion = cast(CreateCompletionResponse, completion)
    return completion["choices"][0]["text"]


def create_remote_completion_iter(
    user_prompt: str,
    system_prompt: str,
) -> Iterator[str]:
    remote_ai_config = config.get_ai_remote()
    client = OpenAI(api_key=remote_ai_config["api_key"])

    system_prompt = REMOTE_SYSTEM_PROMPT_QUERY_TEMPLATE.format(
        db_schema=db.schema()
    )
    response = client.chat.completions.create(
        model=remote_ai_config["model"],
        stream=True,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    for chunk in response:
        yield chunk.choices[0].delta.content or ""


def create_remote_completion_str(
    user_prompt: str, system_prompt: str, temperature: float | None = None
) -> str:
    remote_ai_config = config.get_ai_remote()
    client = OpenAI(api_key=remote_ai_config["api_key"])

    system_prompt = REMOTE_SYSTEM_PROMPT_QUERY_TEMPLATE.format(
        db_schema=db.schema()
    )
    completion = client.chat.completions.create(
        model=remote_ai_config["model"],
        stream=False,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return completion.choices[0].message.content or ""


@dataclass
class QueryResult:
    data: pd.DataFrame
    response: str
    persisted_table_name: str | None = None


# Maybe an improvement could be to either offer an `echo` flag or a way to inject a printer.
def query(user_prompt: str, persist=False, verbose=False) -> QueryResult:
    con = db.connect()
    sql_fence_pattern = r"```sql([\s\S]*?)```"
    ai_config = config.get_ai()
    if ai_config["preference"] == "remote" and ai_config.get("remote"):
        system_prompt = LOCAL_SYSTEM_PROMPT_QUERY_TEMPLATE.format(
            db_schema=db.schema()
        )
        completion = create_remote_completion_str(
            user_prompt, system_prompt, temperature=0
        )
    else:
        system_prompt = LOCAL_SYSTEM_PROMPT_QUERY_TEMPLATE.format(
            db_schema=db.schema()
        )
        completion = create_local_completion_str(
            user_prompt, system_prompt, verbose=verbose, temperature=0
        )

    sql_commands = re.findall(sql_fence_pattern, completion, re.DOTALL)
    if len(sql_commands) == 0:
        return QueryResult(data=pd.DataFrame(), response=completion)

    relation = con.sql(sql_commands[0].strip())

    if persist:
        timestamp = datetime.now().strftime("%Y_%m_%dT%H_%M_%S")
        view_name = f"ai_response_{timestamp}"
        relation.create_view(view_name)
        return QueryResult(
            data=relation.fetchdf(),
            response=completion,
            persisted_table_name=view_name,
        )

    return QueryResult(
        data=relation.fetchdf(),
        response=completion,
    )


def ask_iter(user_prompt: str, verbose: bool) -> Iterator[str]:
    ai_config = config.get_ai()
    if ai_config["preference"] == "remote" and ai_config.get("remote"):
        system_prompt = REMOTE_SYSTEM_PROMPT_ASK_TEMPLATE.format(
            db_schema=db.schema()
        )
        for token in create_remote_completion_iter(user_prompt, system_prompt):
            yield token
    else:
        system_prompt = LOCAL_SYSTEM_PROMPT_ASK_TEMPLATE.format(
            db_schema=db.schema()
        )
        for token in create_local_completion_iter(
            user_prompt, system_prompt, verbose=verbose
        ):
            yield token


def ask_str(user_prompt: str, verbose: bool) -> str:
    ai_config = config.get_ai()
    if ai_config["preference"] == "remote" and ai_config.get("remote"):
        system_prompt = LOCAL_SYSTEM_PROMPT_ASK_TEMPLATE.format(
            db_schema=db.schema()
        )
        completion = create_remote_completion_str(user_prompt, system_prompt)
    else:
        system_prompt = LOCAL_SYSTEM_PROMPT_ASK_TEMPLATE.format(
            db_schema=db.schema()
        )
        completion = create_local_completion_str(
            user_prompt, system_prompt, verbose=verbose
        )

    return completion
