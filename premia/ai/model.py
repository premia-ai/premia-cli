from huggingface_hub import hf_hub_download
from llama_cpp import Llama
from openai import OpenAI
from premia.db import internals
from premia.utils import config, types
from premia.utils.loader import Loader

LOCAL_SYSTEM_PROMPT_TEMPLATE = """
[INST]
You are an text-to-SQL assistant.

You are given context about a database starting with "[CTX]" and ending with "[/CTX]".

You are given a specification for a database query starting with "[SPEC]" and ending with "[/SPEC]".
[/INST]
[CTX]
DuckDB SQL-database schema:
```sql
{db_schema}
```
[/CTX]
[SPEC]
{user_prompt}
[/SPEC]
[INST]
Explain which tables and views are needed for the query. Then write one SQL command to fulfill the specification.

Only include tables, views and columns specified in the context.
[/INST]
"""

REMOTE_SYSTEM_PROMPT_TEMPLATE = """
DuckDB SQL-database schema:
```sql
{db_schema}
```
You are an SQL assistant.

You are given a specification for a database query.

Explain which tables and views are needed for the query. Then write one SQL command to fulfill the specification.

Only include tables, views and columns specified in the mentioned database schema.
"""


def setup_remote_model(api_key: str, model_name: str):
    config.update_remote_ai_config(api_key=api_key, model_name=model_name)


def get_local_model_path(
    link: str | None = None, force_download: bool = False
) -> str:
    ai_config = config.config().ai
    local_ai_config = ai_config.local if ai_config else None

    if link:
        model_id = config.HuggingfaceModelId.parse(link)
        model_path = hf_hub_download(
            repo_id=model_id.repo_id,
            filename=model_id.filename,
            force_download=force_download,
            cache_dir=config.cache_dir(create_if_missing=True),
        )
        config.update_local_ai_config(model_path, model_id)
    elif local_ai_config:
        model_path = hf_hub_download(
            repo_id=local_ai_config.repo_id,
            filename=local_ai_config.filename,
            force_download=force_download,
            cache_dir=config.cache_dir(create_if_missing=True),
        )
    else:
        raise types.ConfigError(
            "You need to either pass a model link or have a local model set up in your config."
        )

    return model_path


def create_local_prompt(user_prompt: str) -> str:
    db_schema = internals.inspect()
    input = LOCAL_SYSTEM_PROMPT_TEMPLATE.format(
        db_schema=db_schema, user_prompt=user_prompt
    )
    return f"{input}</s> "


def create_local_completion(user_prompt: str, verbose: bool) -> str:
    try:
        model_path = get_local_model_path()
    except types.ConfigError:
        raise types.ConfigError("Please set up a local model using `ai init`.")

    model = Llama(
        model_path=model_path,
        n_ctx=8000,
        n_threads=7,
        n_gpu_layers=0,
        verbose=verbose,
    )

    completion = model(
        create_local_prompt(user_prompt),
        max_tokens=2048,
        echo=True,
        stream=True,
        top_k=0,
    )

    loader = Loader()
    loader.start()

    complete_response = ""
    for response in completion:
        loader.stop()
        token = (
            response
            if isinstance(response, str)
            else response["choices"][0]["text"]
        )
        print(token, end="", flush=True)
        complete_response += token
    print()

    return complete_response


def create_remote_completion(user_prompt: str, ai_client: OpenAI) -> str:
    ai_config = config.config().ai
    if not ai_config or not ai_config.remote:
        raise types.ConfigError("No remote AI model setup.")

    db_schema = internals.inspect()
    system_prompt = REMOTE_SYSTEM_PROMPT_TEMPLATE.format(db_schema=db_schema)
    stream = ai_client.chat.completions.create(
        model=ai_config.remote.model,
        stream=True,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    loader = Loader()
    loader.start()

    complete_response = ""
    for chunk in stream:
        loader.stop()
        token = chunk.choices[0].delta.content or ""
        print(token, end="", flush=True)
        complete_response += token
    print()

    return complete_response
