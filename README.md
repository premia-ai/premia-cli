# Premia Cli

_AI co-pilot for asset managers._

## Demo

[![Premia Demo](https://cdn.loom.com/sessions/thumbnails/9dad48f3775d4fa0ba76df6e65765cf9-with-play.gif)](https://www.loom.com/embed/9dad48f3775d4fa0ba76df6e65765cf9?sid=0f640b6c-f8f0-4d41-9806-82e8dcee5d86)

## How can I try it?

The easiest way to try Premia is to follow the following steps:

```sh
# Download project
$ git clone https://github.com/premia-ai/cli premia-cli
$ cd premia-cli

# Install project
$ chmod +x bin/install.sh
$ bin/install.sh

# Set up sample DB and optionally import data
$ premia db init

# Set up local AI
$ premia ai init
```

## Setup

Run the following commands in your terminal from the repo's folder, to install the `premia` command.

```sh
$ chmod +x bin/install.sh
$ bin/install.sh
```

## Commands

### `config`

#### `ai`

Show the AI configuration

<details>
<summary><b>Example</b></summary>
<br>

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

</details>

#### `db`

Show the database configuration

<details>
<summary><b>Example</b></summary>
<br>

```sh
$ premia config db

Type: DuckDB
Instruments:
  Stocks:
    Raw Data: stocks_1_minute_candles
    Timespan: minute
```

</details>

### `ai`

The `ai` command allows you to setup and use an open source LLM to interact with your infrastructure.

#### `set-model`

`set-model` allows you to download an open source LLM like Mistral's 7B model or connect to a proprietary model like OpenAI's GPT-4.

<details>
<summary><b>Example: Set up open source model</b></summary>
<br>

If you want to set up an open source model like Mistral 7B or Mixtral 8x7B you can just run the following command.

You can use any other open source LLM. Just copy the link to the GGUF file from [HuggingFace](https://huggingface.co).

```sh
# For Mistral 7B
$ premia ai set-model local "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/blob/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"

# For Mixtral 8x7B
$ premia ai set-model local "https://huggingface.co/TheBloke/Mixtral-8x7B-Instruct-v0.1-GGUF/blob/main/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"
```

</details>

<details>
<summary><b>Example: Set up a remote model (OpenAI)</b></summary>
<br>

If you want to set up a remote LLM from OpenAI you can do so as well. With the `--model` flag you can define which OpenAI model you would like to use. The command defaults to the GPT-3.5 Turbo model)

```sh
# For GPT-3.5 Turbo (default)
$ premia ai set-model remote "sk-example-api-key"

# For GPT-4
$ premia ai set-model remote "sk-example-api-key" --model "gpt-4"
```

</details>

#### `set-preference`

Set the preference for which model should be used for the query executions.

<details>
<summary><b>Example</b></summary>
<br>


```sh
$ premia set-preference remote
```

</details>

#### `query`

With `query` you can ask the LLM to create SQL commands for you to query your db. The flow allows for multiple steps.

<details>
<summary><b>Example</b></summary>
<br>

````sh
$ premia ai query 'Get the average stock price of a company with the name "Tesla Inc." for the year 2024'

```sql
SELECT AVG(stocks_1_day_candles.close) as avg_price
FROM companies
JOIN stocks_1_day_candles ON companies.symbol = stocks_1_day_candles.symbol
WHERE companies.name = 'Tesla Inc.' AND EXTRACT(YEAR FROM stocks_1_day_candles.bucket) = 2024;
```
````

</details>

### `db`

The `db` command allows to setup or interact with an SQL database for financial data.

#### `init`

`init` will set up a DuckDB database structured to store financial data.

#### `setup`

`setup` allows you to connect your DuckDB to Premia or to create a new DuckDB for premia

<details>
<summary><b>Example</b></summary>
<br>

```sh
# Create a new DB for premia
$ premia db setup

# Connect Premia to a DB called `securities.db` in the home directory
$ premia db setup --path ~/securities.db
```

</details>

#### `schema`

The `schema` command will print your database's schema to stdout.

<details>
<summary><b>Example</b></summary>
<br>

Here an example of a database that has two tables set up (`contracts` and `options_1_hour_candles`).

```sh
$ premia db schema

CREATE TABLE contracts (
  symbol VARCHAR NOT NULL,
  expiration_date TIMESTAMP WITH TIME ZONE NOT NULL,
  company_symbol VARCHAR NOT NULL,
  contract_type VARCHAR NOT NULL,
  shares_per_contract INTEGER NOT NULL,
  strike_price DECIMAL(18,3) NOT NULL,
  currency VARCHAR NULL
);

CREATE TABLE options_1_hour_candles (
  time TIMESTAMP WITH TIME ZONE NOT NULL,
  symbol VARCHAR NOT NULL,
  open DECIMAL(18,3) NULL,
  close DECIMAL(18,3) NULL,
  high DECIMAL(18,3) NULL,
  low DECIMAL(18,3) NULL,
  volume INTEGER NULL,
  currency VARCHAR NOT NULL,
  data_provider VARCHAR NOT NULL
);
```

</details>


#### `tables`

The `tables` command will print the tables that are visible to Premia's AI to stdout.

<details>
<summary><b>Example</b></summary>
<br>

```sh
$ premia db tables

companies
contracts
options_1_hour_candles
stocks_1_day_candles
stocks_1_minute_candles
stocks_1_minute_returns
```

</details>

#### `table`

The `table` command takes a table name as input and shows a sample of the table's content.

<details>
<summary><b>Example</b></summary>
<br>

Here an example of a database that includes a table called `contracts`.

```sh
$ premia db table contracts

┌─────────────────────┬──────────────────────┬───┬───────────────┬──────────┐
│       symbol        │   expiration_date    │ … │ strike_price  │ currency │
│       varchar       │ timestamp with tim…  │   │ decimal(18,3) │ varchar  │
├─────────────────────┼──────────────────────┼───┼───────────────┼──────────┤
│ AMZN240202C00080000 │ 2024-02-02 00:00:0…  │ … │        80.000 │ USD      │
│ AMZN240202C00085000 │ 2024-02-02 00:00:0…  │ … │        85.000 │ USD      │
│ AMZN240202C00090000 │ 2024-02-02 00:00:0…  │ … │        90.000 │ USD      │
│ AMZN240202P00080000 │ 2024-02-02 00:00:0…  │ … │        80.000 │ USD      │
│ AMZN240202P00085000 │ 2024-02-02 00:00:0…  │ … │        85.000 │ USD      │
│ AMZN240202P00090000 │ 2024-02-02 00:00:0…  │ … │        90.000 │ USD      │
│ GOOG240202C00075000 │ 2024-02-02 00:00:0…  │ … │        75.000 │ USD      │
│ GOOG240202C00095000 │ 2024-02-02 00:00:0…  │ … │        95.000 │ USD      │
│ GOOG240202C00100000 │ 2024-02-02 00:00:0…  │ … │       100.000 │ USD      │
│ GOOG240202P00095000 │ 2024-02-02 00:00:0…  │ … │        95.000 │ USD      │
│          ·          │          ·           │ · │           ·   │  ·       │
│          ·          │          ·           │ · │           ·   │  ·       │
│          ·          │          ·           │ · │           ·   │  ·       │
│ AAPL240202C00090000 │ 2024-02-02 00:00:0…  │ … │        90.000 │ USD      │
│ AAPL240202P00080000 │ 2024-02-02 00:00:0…  │ … │        80.000 │ USD      │
│ AAPL240202P00090000 │ 2024-02-02 00:00:0…  │ … │        90.000 │ USD      │
│ AAPL240202P00100000 │ 2024-02-02 00:00:0…  │ … │       100.000 │ USD      │
│ MSFT240202C00250000 │ 2024-02-02 00:00:0…  │ … │       250.000 │ USD      │
│ MSFT240202C00260000 │ 2024-02-02 00:00:0…  │ … │       260.000 │ USD      │
│ MSFT240202C00265000 │ 2024-02-02 00:00:0…  │ … │       265.000 │ USD      │
│ MSFT240202P00190000 │ 2024-02-02 00:00:0…  │ … │       190.000 │ USD      │
│ MSFT240202P00200000 │ 2024-02-02 00:00:0…  │ … │       200.000 │ USD      │
│ MSFT240202P00210000 │ 2024-02-02 00:00:0…  │ … │       210.000 │ USD      │
├─────────────────────┴──────────────────────┴───┴───────────────┴──────────┤
│ 42 rows (20 shown)                                    7 columns (4 shown) │
└───────────────────────────────────────────────────────────────────────────┘
```

</details>

#### `available-features`

The `available-features` command lists all of the features that you can set up for an instrument.

<details>
<summary><b>Example</b></summary>
<br>

```sh
$ premia db available-features

moving_averages
returns
volume_changes
```

</details>

#### `import`

The `import` command allows to import data from common financial dataproviders (polygon.io, twelvedata.com and yfinance) or a CSV file.

## For contributors

Feel free to open a Github issue if you want to add functionality to Premia! We are looking forward to talking to you.

### Setup

We manage the repo with [`Pipenv`](https://pipenv.pypa.io/en/latest/#install-pipenv-today).

To install the project's dependencies run

```sh
$ pipenv install
```

To run the project while working on it run

```sh
$ pipenv run python -m premia
```
