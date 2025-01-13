-- Encryption extensions to secure access_keys to Plaid
CREATE EXTENSION pgcrypto ;

-- Create SQL structure to accept Plaid API data

CREATE TABLE accounts (
    account_id VARCHAR(255) PRIMARY KEY,
    mask VARCHAR(255),
    name VARCHAR(255),
    official_name VARCHAR(255),
    persistent_account_id VARCHAR(255),
    subtype VARCHAR(255),
    type VARCHAR(255),
    user_email VARCHAR(255),
    user_phone VARCHAR(20),
    plaid_access_token BYTEA
);

CREATE TABLE accounts_balance_history (
    id SERIAL PRIMARY KEY,  
    account_id VARCHAR(255),
    balances_available FLOAT,
    balances_current FLOAT,
    balances_iso_currency_code VARCHAR(10),
    balances_limit FLOAT,
    balances_unofficial_currency_code VARCHAR(10),
    balances_datetime TIMESTAMP,
    CONSTRAINT fk_account FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);


CREATE TABLE transactions (
    transaction_id VARCHAR(255) PRIMARY KEY,
    account_id VARCHAR(255), 
    amount FLOAT,
    authorized_date	date,
    category_id	VARCHAR(20), 
	date date,
    iso_currency_code VARCHAR(20),
    logo_url VARCHAR(255), 
    merchant_entity_id VARCHAR(255), 
    merchant_name VARCHAR(255), 
    name VARCHAR(255), 
    payment_channel	VARCHAR(255), 
    pending BOOLEAN,
    personal_finance_category_icon_url VARCHAR(255), 
    website VARCHAR(255),
    personal_finance_category_detailed VARCHAR(255),
    personal_finance_category VARCHAR(255),
    CONSTRAINT fk_account FOREIGN KEY (account_id) REFERENCES accounts(account_id)

);

-- Analytical views

CREATE VIEW v_latest_account_balance AS
SELECT DISTINCT ON (account_id) *
FROM accounts_balance_history
ORDER BY account_id, balances_datetime DESC;



