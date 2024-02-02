# Premia Cli

Premia is an AI co-pilot to manage financial data systems.

## Demo

[![Premia Demo](https://cdn.loom.com/sessions/thumbnails/d9c49e1b14834a36a1d8cda5174d17a0-with-play.gif)](https://www.loom.com/share/d9c49e1b14834a36a1d8cda5174d17a0?sid=5f6c93ae-ea47-4d01-a459-f229572ec71a)

## Setup

Run the following commands in your terminal from the repo's folder, to install the `premia` command.

```sh
chmod +x bin/install.sh
bin/install.sh
```

## Commands

### `ai`

The `ai` command allows you to setup and use an open source LLM to interact with your infrastructure.

#### `init`

You can download an LLM using `init`. By default it will install the Mistral 7B model.

**Example**
```sh
premia ai init  
```

#### `query`

With `query` you can ask the LLM to create SQL commands for you to query your db. The flow allows for multiple steps.

**Example**
```sh
premia ai query 'Get the average stock price of a company with the name "Tesla Inc." for the year 2024'

\`\`\`sql
SELECT AVG(stocks_1_day_candles.close) as avg_price
FROM companies
JOIN stocks_1_day_candles ON companies.symbol = stocks_1_day_candles.symbol
WHERE companies.name = 'Tesla Inc.' AND EXTRACT(YEAR FROM stocks_1_day_candles.bucket) = 2024;
\`\`\`
```

### `db`

The `db` command allows to setup or interact with an SQL database for financial data.

#### `init`

`init` will set up a DuckDB database structured to store financial data.

#### `schema`

The `schema` command will print your database's schema to stdout.

#### `tables`

The `tables` command will print the tables that are visible to Premia's AI to stdout.

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
