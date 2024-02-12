# Premia Cli

Premia is an AI co-pilot to manage financial data systems.

## Demo

[![Premia Demo](https://cdn.loom.com/sessions/thumbnails/9dad48f3775d4fa0ba76df6e65765cf9-with-play.gif)](https://www.loom.com/embed/9dad48f3775d4fa0ba76df6e65765cf9?sid=0f640b6c-f8f0-4d41-9806-82e8dcee5d86)

## How can I try it?

The easiest way to try Premia is to follow the following steps:

```sh
# Download project
git clone https://github.com/premia-ai/cli premia-cli
cd premia-cli

# Install project
chmod +x bin/install.sh
bin/install.sh

# Set up sample DB and optionally import data
premia db init

# Set up local AI
premia ai init
```

## Setup

Run the following commands in your terminal from the repo's folder, to install the `premia` command.

```sh
chmod +x bin/install.sh
bin/install.sh
```

## Commands

### `config`

#### `ai`

Show the AI configuration

**Example**
```sh
$ premia config ai

Preference: local
Remote:
  OpenAI Details:
    API-Key: sk-example-api-key
    Model: gpt-3.5-turbo
Local:
  Huggingface Details:
    User: TheBloke
    Repo: Mistral-7B-Instruct-v0.2-GGUF
    Filename: mistral-7b-instruct-v0.2.Q4_K_M.gguf
```

#### `db`

Show the database configuration

**Example**
```sh
$ premia config db

Type: DuckDB
Instruments:
  Stocks:
    Raw Data: stocks_1_minute_candles
    Timespan: minute
```

### `ai`

The `ai` command allows you to setup and use an open source LLM to interact with your infrastructure.

#### `setup`

`setup` allows you to download an open source LLM like Mistral's 7B model or connect to a proprietary model like OpenAI's GPT-4.

**Example**

If you want to set up Mistral 7B you can just run the following command.

```sh
$ premia ai setup local "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/blob/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
```

**Example**

If you want to use another open source LLM you can do so by specifying a repo and GGUF file from [HuggingFace](https://huggingface.co).

Here another example using Mistral's bigger 8x7B Mixtral model.

```sh
$ premia ai setup local "https://huggingface.co/TheBloke/Mixtral-8x7B-Instruct-v0.1-GGUF/blob/main/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"
```

**Example**

If you want to set up a remote LLM from OpenAI you can do so as well (the `--model` flag is optional and defaults to `"gpt-3.5-turbo"`)

```sh
$ premia ai setup remote "sk-example-api-key" --model "gpt-4"
```

#### `query`

With `query` you can ask the LLM to create SQL commands for you to query your db. The flow allows for multiple steps.

**Example**
````sh
$ premia ai query 'Get the average stock price of a company with the name "Tesla Inc." for the year 2024'

```sql
SELECT AVG(stocks_1_day_candles.close) as avg_price
FROM companies
JOIN stocks_1_day_candles ON companies.symbol = stocks_1_day_candles.symbol
WHERE companies.name = 'Tesla Inc.' AND EXTRACT(YEAR FROM stocks_1_day_candles.bucket) = 2024;
```
````

### `db`

The `db` command allows to setup or interact with an SQL database for financial data.

#### `init`

`init` will set up a DuckDB database structured to store financial data.

#### `setup`

`setup` allows you to connect your DuckDB to Premia or to create a new DuckDB for premia

**Example**

```sh
# Create a new DB for premia
$ premia db setup

# Connect Premia to a DB called `securities.db` in the home directory
$ premia db setup --path ~/securities.db
```

#### `schema`

The `schema` command will print your database's schema to stdout.

#### `tables`

The `tables` command will print the tables that are visible to Premia's AI to stdout.

#### `table`

The `table` command takes a table name as input and shows a sample of the table's content.

#### `import`

The `import` command allows to import data from common financial dataproviders (polygon.io, twelvedata.com and yfinance) or a CSV file.

## For contributors

Feel free to open a Github issue if you want to add functionality to Premia! We are looking forward to talking to you.

### Setup

We manage the repo with [`Pipenv`](https://pipenv.pypa.io/en/latest/#install-pipenv-today).

To install the project's dependencies run

```sh
pipenv install
```

To run the project while working on it run

```sh
pipenv run python -m premia
```
