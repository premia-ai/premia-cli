# Premia Cli

Premia allows to bootstrap financial data infrastructure for asset management firms.

## Installation

Run the following in your terminal from the repo, to install `premia`

```sh
bin/install.sh
```

## Subcommands

### `db`

The `db` subcommand allows to setup or interact with an SQL database for financial data.

### `init`

`init` will set up a duckdb instance structured to store financial data.

### `inpect`

The `inspect` command will show your database's schema.

### `import`

The `import` command allows to import data from dataproviders or a CSV file into your db.

### `ai`

The `ai` subcommand allows to setup and use an open source LLM to interact with your infrastructure.

#### `init`

You can download an LLM using `init`. By default it will install the Mistral 7B model.

**Example**
```sh
premia ai init  
```

#### `query`

With `query` you can ask the LLM to create an SQL query for you to query your db.

**Example**
```sh
premia ai query 'Query the average stock price of a company with the name "Tesla Inc." for the year 2024'

SELECT AVG(stocks_1_day_candles.close) as avg_price
FROM companies
JOIN stocks_1_day_candles ON companies.symbol = stocks_1_day_candles.symbol
WHERE companies.name = 'Tesla Inc.' AND EXTRACT(YEAR FROM stocks_1_day_candles.bucket) = 2024;
```

### `db`

Subcommand to initialize and query your financial database.

#### `init`

Setup a financial database

#### `seed` (TODO)

Import data from data providers like Polygon and TwelveData.

#### `inspect`

Inspects your Postgres database and prints out the schema.

## Dev Requirements

We manage the repo with [`Pipenv`](https://pipenv.pypa.io/en/latest/#install-pipenv-today).

