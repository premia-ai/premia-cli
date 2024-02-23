CREATE TABLE IF NOT EXISTS contracts (
    symbol TEXT NOT NULL,
    expiration_date TIMESTAMPTZ NOT NULL,
    company_symbol TEXT NOT NULL,
    contract_type TEXT NOT NULL,
    shares_per_contract INT NOT NULL,
    strike_price DECIMAL NOT NULL,
    currency TEXT
);
