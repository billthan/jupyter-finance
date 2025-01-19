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

CREATE TABLE fin_refresh (
    id SERIAL PRIMARY KEY,  
    refresh_type VARCHAR(20),
    refresh_time TIMESTAMP,
	refresh_status boolean,
	refresh_description VARCHAR(255)
);

CREATE TABLE budget (
    id SERIAL PRIMARY KEY,  
    name VARCHAR(255) NOT NULL,                    
    description VARCHAR(255),                      
    balance_limit NUMERIC(10, 2) NOT NULL,         
    refresh_cadence VARCHAR(20) NOT NULL,          
    refresh_day_of_week VARCHAR(10),             
    is_deleted BOOLEAN DEFAULT FALSE              
);

CREATE TABLE budget_batch (
    id SERIAL PRIMARY KEY,  
    budget_id INT NOT NULL,                        
    start_date TIMESTAMP NOT NULL,                
    end_date TIMESTAMP NOT NULL,                
    current_balance NUMERIC(10, 2) NOT NULL,      
    under_limit BOOLEAN NOT NULL,                  
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_budget FOREIGN KEY (budget_id) REFERENCES budget(id) ON DELETE CASCADE
);

CREATE TABLE budgeted_transaction (
    id SERIAL PRIMARY KEY,  
    batch_id INT NOT NULL,                     
    transaction_id VARCHAR(255) NOT NULL,        
    verified_date TIMESTAMP,                      
    CONSTRAINT fk_batch FOREIGN KEY (batch_id) REFERENCES budget_batch(id) ON DELETE CASCADE,
    CONSTRAINT fk_transaction FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
);


-- Analytical views

CREATE VIEW v_latest_account_balance AS
SELECT DISTINCT ON (account_id) *
FROM accounts_balance_history
ORDER BY account_id, balances_datetime DESC;

CREATE VIEW v_lastest_budget_batches AS
SELECT *
FROM public.budget_batch bb
WHERE bb.end_date = (
    SELECT MAX(end_date)
    FROM public.budget_batch bb_sub
    WHERE bb_sub.budget_id = bb.budget_id
);
