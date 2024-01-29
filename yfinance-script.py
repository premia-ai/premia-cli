import yfinance as yf
import pandas as pd
from datetime import datetime

end_date = datetime.now().strftime("%Y-%m-%d")

companies = ["AMZN", "GOOG", "NVDA", "TSLA", "META", "AAPL", "MSFT"]
companies_tickers = yf.Tickers(companies)
companies_tickers_history = companies_tickers.history(
    period="max",
    end=end_date,
    interval="1m",
)

companies_tickers_history.stack(level=1).rename_axis(
    ["Time", "Ticker"]
).reset_index(level=1).drop(columns=["Dividends", "Stock Splits"]).rename(
    columns=str.lower
).rename_axis(
    "time"
).to_csv(
    "all_data.csv"
)

companies_individual_tickers = [yf.Ticker(company) for company in companies]
companies_info = [
    company_ticker.get_info() for company_ticker in companies_individual_tickers
]
fundamentals_df = pd.DataFrame(companies_info)[
    ["shortName", "symbol", "industry", "sector", "country"]
]
fundamentals_df.to_csv("all_fundamentals.csv", index=False)
