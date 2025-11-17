CREATE TABLE IF NOT EXISTS deposits (
    txid TEXT PRIMARY KEY,
    coin TEXT NOT NULL,
    user_id BIGINT NOT NULL,
    status TEXT DEFAULT 'NEW',
    confs INT DEFAULT 0,
    required_confs INT,
    inserted_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    target_address TEXT,
    onchain_amount NUMERIC(38,18)
);

CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    usdt_trc20_address TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_deposits_status ON deposits(status);
