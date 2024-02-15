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

### `ai`

The `ai` command allows you to setup and use an open source LLM to interact with your infrastructure.

#### `config`

Show the AI configuration.

<details>
<summary><b>Example</b></summary>
<br>

```sh
$ premia ai config

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

#### `add`

`add` allows you to download an open source LLM like Mistral's 7B model or connect to a proprietary model like OpenAI's GPT-4.

<details>
<summary><b>Example: Set up open source model</b></summary>
<br>

If you want to set up an open source model like Mistral 7B or Mixtral 8x7B you can just run the following command.

You can use any other open source LLM. Just copy the link to the GGUF file from [HuggingFace](https://huggingface.co).

```sh
# For Mistral 7B
$ premia ai add local "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/blob/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"

# For Mixtral 8x7B
$ premia ai add local "https://huggingface.co/TheBloke/Mixtral-8x7B-Instruct-v0.1-GGUF/blob/main/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"
```

</details>

<details>
<summary><b>Example: Set up a remote model (OpenAI)</b></summary>
<br>

If you want to set up a remote LLM from OpenAI you can do so as well. With the `--model` flag you can define which OpenAI model you would like to use. The command defaults to the GPT-3.5 Turbo model)

```sh
# For GPT-3.5 Turbo (default)
$ premia ai add remote "sk-example-api-key"

# For GPT-4
$ premia ai add remote "sk-example-api-key" --model "gpt-4"
```

</details>

#### `preference`

Set the preference for which model should be used for the query executions.

<details>
<summary><b>Example</b></summary>
<br>


```sh
$ premia ai preference remote
```

</details>

#### `remove`

`remove` lets you remove a model that you have set up previously. Just specify whether you want to remove the `local` or `remote` model.

<details>
<summary><b>Example</b></summary>
<br>


```sh
$ premia ai remove remote
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

#### `config`

Show the database configuration.

<details>
<summary><b>Example</b></summary>
<br>

```sh
$ premia db config

Type: DuckDB
Instruments:
  Stocks:
    Metadata Table: companies
    Timespan: minute
```

</details>

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

#### `features`

The `features` command lists all of the features that you can set up for an instrument.

<details>
<summary><b>Example</b></summary>
<br>

```sh
$ premia db features

moving_averages
returns
volume_changes
```

</details>

#### `add`

The `add` command allows to conveniently specify how you want to set up an instrument, and which featues and aggregates you would like to add.

You can add a new instrument or add new tables to an instrument by specifying `--feature` or `--aggregate-frequency`.

<details>
<summary><b>Example: Add stock tables</b></summary>
<br>

```sh
$ premia db add stocks --raw-frequency second
```

</details>


<details>
<summary><b>Example: Add aggregate tables to existing stock setup</b></summary>
<br>

```sh
$ premia db add stocks --aggregate-frequency hour --aggregate-frequency day
```

</details>

#### `import`

You can import CSV data for your instruments using `import`.

<details>
<summary><b>Example: Using the sample data in the repo</b></summary>
<br>

```sh
$ premia db import stocks --candles-path ./sample_data/sample_stocks_1_minute_candles.csv --metadata-path ./sample_data/sample_companies.csv
```

</details>


#### `remove`

The `remove` command allows to remove tables you have set up with Premia.

<details>
<summary><b>Example: Remove instrument</b></summary>
<br>

```sh
$ premia db remove stocks
```

</details>

<details>
<summary><b>Example: Remove aggregate table for an instrument</b></summary>
<br>

```sh
$ premia db remove stocks --aggregate-frequency day
```

</details>

#### `reset`

The `reset` command will delete your whole database and set up a fresh version.

<details>
<summary><b>Example: With confirmation</b></summary>
<br>

```sh
$ premia db reset

Are you sure you want to reset your database? [y/N]:
```

</details>

<details>
<summary><b>Example: Without confirmation</b></summary>
<br>

You can skip the confirmation with `--yes` or `-y`:
```sh
$ premia db reset --yes
```

</details>

#### `purge`

The `purge` command removes the cached AI responses that you can create.

<details>
<summary><b>Example</b></summary>
<br>

```sh
$ premia db purge
```

</details>

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
