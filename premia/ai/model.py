from huggingface_hub import hf_hub_download
from llama_cpp import Llama
from db import postgres
from utils.loader import Loader

SYSTEM_PROMPT_TEMPLATE = """
PostgreSQL database schema:
```sql
{db_schema}
```
[INST]
You are an SQL assistant.

You are given a specification for a database query starting with "[SPEC]" and ending with "[/SPEC]".

Based two things:
  1. Reason about the steps you need to take to for the query.
  2. Create a well formatted SQL query based on your reasoning.

Only include tables specified in the mentioned PostgreSQL database schema.
[/INST]
"""


def init(
    force=False,
    model_name="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
    model_file="mistral-7b-instruct-v0.2.Q4_K_M.gguf",
) -> str:
    model_path = hf_hub_download(
        model_name, filename=model_file, force_download=force
    )
    return model_path


def create_completion(user_prompt: str, verbose: bool):
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

    db_schema = postgres.inspect()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(db_schema=db_schema)
    input = f"{system_prompt}[SPEC]{user_prompt}[/SPEC]</s> "

    responses = llm(input, **generation_kwargs)

    loader = Loader()
    loader.start()

    for response in responses:
        loader.stop()
        token = (
            response
            if isinstance(response, str)
            else response["choices"][0]["text"]
        )
        print(token, end="", flush=True)
    print()
