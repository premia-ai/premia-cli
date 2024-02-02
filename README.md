# Premia Cli

Premia allows to manage financial data infrastructure using an AI co-pilot.

## Demo

[![Premia Demo](https://cdn.loom.com/sessions/thumbnails/d9c49e1b14834a36a1d8cda5174d17a0-with-play.gif)](https://www.loom.com/share/d9c49e1b14834a36a1d8cda5174d17a0?sid=5f6c93ae-ea47-4d01-a459-f229572ec71a)

## Setup

Run the following in your terminal from the repo, to install `premia`

```sh
bin/install.sh
```

## Subcommands

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

The `db` subcommand allows to setup or interact with an SQL database for financial data.

#### `init`

`init` will set up a duckdb instance structured to store financial data.

#### `schema`

The `schema` command will print your database's schema to stdout.

#### `tables`

The `tables` command will print the tables of your database to stdout.

#### `import`

The `import` command allows to import data from dataproviders or a CSV file into your db.


## Dev Requirements

We manage the repo with [`Pipenv`](https://pipenv.pypa.io/en/latest/#install-pipenv-today).

