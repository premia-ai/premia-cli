from huggingface_hub import hf_hub_download
from llama_cpp import Llama
from openai import OpenAI
from premia.db import internals
from premia.utils.loader import Loader

LOCAL_SYSTEM_PROMPT_TEMPLATE = """
DuckDB SQL-database schema:
```sql
{db_schema}
```
[INST]
You are an SQL assistant.

You are given a specification for a database query starting with "[SPEC]" and ending with "[/SPEC]".

Explain which tables and views are needed for the query. Then write one SQL command to fulfill the specification.

Only include tables, views and columns specified in the mentioned database schema.
[/INST]
"""

REMOTE_SYSTEM_PROMPT_TEMPLATE = """
DuckDB SQL-database schema:
```sql
{db_schema}
- contact-type: 'call' or 'put'
```
You are an SQL assistant.

You are given a specification for a database query.

Explain which tables and views are needed for the query. Then write one SQL command to fulfill the specification.

Only include tables, views and columns specified in the mentioned database schema.
"""


def init(
    force=False,
    model_repo="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
    model_file="mistral-7b-instruct-v0.2.Q4_K_M.gguf",
) -> str:
    model_path = hf_hub_download(
        model_repo, filename=model_file, force_download=force
    )
    return model_path


def create_ai_prompt(user_prompt: str) -> str:
    db_schema = internals.inspect()
    system_prompt = LOCAL_SYSTEM_PROMPT_TEMPLATE.format(db_schema=db_schema)
    input = f"{system_prompt}[SPEC]{user_prompt}[/SPEC]</s> "
    return input


def create_local_completion(user_prompt: str, verbose: bool) -> str:
    model_path = init()
    llm = Llama(
        model_path=model_path,
        n_ctx=8000,
        n_threads=7,
        n_gpu_layers=0,
        verbose=verbose,
    )

    generation_kwargs = {
        "max_tokens": 2048,
        "echo": True,
        "stream": True,
        "top_k": 0,
    }

    input = create_ai_prompt(user_prompt)
    completion = llm(input, **generation_kwargs)

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
    db_schema = internals.inspect()
    system_prompt = REMOTE_SYSTEM_PROMPT_TEMPLATE.format(db_schema=db_schema)
    stream = ai_client.chat.completions.create(
        model="gpt-3.5-turbo",
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
