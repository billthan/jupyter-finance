# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/core.ipynb.

# %% auto 0
__all__ = ['PLAID_COUNTRY_CODES', 'PLAID_PRODUCTS', 'PLAID_CLIENT_ID', 'PLAID_SECRET', 'PLAID_ENV', 'PLAID_BASE_URL',
           'POSTGRES_DB', 'POSTGRES_HOST', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_ENCRYPTION_KEY',
           'plaid_post', 'get_account', 'get_account_transactions', 'get_account_df', 'get_accounts_df',
           'get_transactions_df', 'db_conn', 'db_sql', 'get_stored_public_access_tokens', 'insert_account_df',
           'insert_transactions_df', 'upsert_account_balances_df', 'generate_link_token', 'get_and_save_public_token',
           'get_and_save_all_account_transactions', 'get_and_save_balance_history', 'about']

# %% ../nbs/core.ipynb 3
import os, uuid, json, datetime, requests, psycopg2
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Optional, Dict, Any, List, Tuple
from nbdev.showdoc import DocmentTbl


# %% ../nbs/core.ipynb 4
PLAID_COUNTRY_CODES = ['CA','US']
PLAID_PRODUCTS = ['transactions']
PLAID_CLIENT_ID= os.environ['PLAID_CLIENT_ID']
PLAID_SECRET= os.environ['PLAID_SECRET']
PLAID_ENV = os.environ['PLAID_ENV']
PLAID_BASE_URL = f'https://{PLAID_ENV}.plaid.com'

POSTGRES_DB="finances"
POSTGRES_HOST= "db"
POSTGRES_USER= os.environ['POSTGRES_USER']
POSTGRES_PASSWORD= os.environ['POSTGRES_PASSWORD']
POSTGRES_ENCRYPTION_KEY=os.environ['POSTGRES_ENCRYPTION_KEY']

# %% ../nbs/core.ipynb 6
def plaid_post(
    endpoint: str, # The specific Plaid API endpoint (e.g., "accounts/get"), refer to [Plaid API Docs](https://plaid.com/docs/api/)
    payload: Dict[str, Any], # The JSON payload to be sent with the request
) -> Dict[str, Any]: # Returns JSON response from Plaid API
    """
    Makes a POST request to the Plaid API.
    """
    url = f"{PLAID_BASE_URL}/{endpoint}"  
    headers = {'Content-Type': 'application/json'} 
    response = requests.post(url, headers=headers, data=json.dumps(payload))  
    return response.json()  


def get_account(
    access_token: str  # The Plaid access token for the user account
) -> Dict[str, Any]: # Returns Dictionary object of accounts
    """
    Retrieves account details from the Plaid API.
    """
    payload = {
        "client_id": PLAID_CLIENT_ID,  
        "secret": PLAID_SECRET,        
        "access_token": access_token   
    }
    accounts_response = plaid_post("accounts/get", payload)
    return accounts_response  


def get_account_transactions(
    access_token: str,  # The Plaid access token for the user account
    start_date: str,    # The starting date for transactions (YYYY-MM-DD)
    end_date: str       # The ending date for transactions (YYYY-MM-DD)
) -> List[Dict[str, Any]]: # Returns List objects containing Dictionary objects related to account transactions
    """
    Retrieves all transactions for an account from the Plaid API.
    """
    try:
        transactions = []  # Initialize an empty list to hold transactions
        payload = {
            "client_id": PLAID_CLIENT_ID, 
            "secret": PLAID_SECRET,       
            "access_token": access_token,  
            "start_date": start_date,      
            "end_date": end_date,          
            "options": {
                "count": 100,  # Pagination
                "offset": 0   
            }
        }

        while True:
            transactions_response = plaid_post("transactions/get", payload)  
            transactions.extend(transactions_response.get("transactions", [])) 
            
            if len(transactions) >= transactions_response.get("total_transactions", 0):
                break
            
            payload["options"]["offset"] += 100

        return transactions  
    except Exception as e:
        print(f"There was an error. Please report outputs of this cell to the developer:\n{e}")
        raise


# %% ../nbs/core.ipynb 8
def get_account_df(
    accounts_response: dict # Dictionary object containing accounts
) -> pd.DataFrame: # Returns  Dataframe of individual account
    """
    Converts account information from the Plaid API response into a pandas DataFrame.
    """
    return pd.json_normalize(accounts_response, sep='_')


def get_accounts_df(
    access_tokens: List[Tuple[str]] # List object containing access tokens
) -> pd.DataFrame: # Returns Dataframe of accounts
    """
    Retrieves and merges account information for multiple access tokens into a single pandas DataFrame.
    """
    accounts_df_list = []

    for single_access_token in access_tokens:
        account_data = get_account(single_access_token[0])
        account_df = get_account_df(account_data)
        print(account_df.head())
        display(account_df)
        accounts_df_list.append(account_df)

    return pd.concat(accounts_df_list, ignore_index=True)


def get_transactions_df(
    access_tokens: List[Tuple[str]],  # List object containing access tokens
    start_date: str = None,           # Optional start date (YYYY-MM-DD)
    end_date: str = None              # Optional end date (YYYY-MM-DD)
) -> pd.DataFrame:
    """
    Retrieves and converts transaction data for multiple access tokens into a pandas DataFrame.
    """
    transactions_list = []
    if not start_date:
        start_date = (datetime.today() - relativedelta(years=1)).strftime('%Y-%m-%d')
        end_date = datetime.today().strftime('%Y-%m-%d')
    print(f"Starting to get all transactions between {start_date} and {end_date}")
    for single_access_token in access_tokens:
        transactions_list.extend(get_account_transactions(single_access_token[0], start_date, end_date))

    return pd.json_normalize(transactions_list)


# %% ../nbs/core.ipynb 10
def db_conn(
) -> psycopg2.extensions.connection:  # psycopg2 connection to database
    """
    Creates and returns a connection to the PostgreSQL database.
    """
    try:
        return psycopg2.connect(
            host=POSTGRES_HOST,
            database="finances",
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
    except psycopg2.OperationalError as e:
        print(f"Database connection skipped: {e}")
        return None


def db_sql(
    query: str  # The string representation of SQL query to execute
) -> pd.DataFrame: # Dataframe of executed SQL query
    """
    Executes a defined SQL query and returns the result as a pandas DataFrame.
    """
    engine = create_engine(
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"
    )
    try:
        return pd.read_sql_query(query, engine)
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()
    finally:
        engine.dispose()


def get_stored_public_access_tokens() -> List[Tuple[str]]: # Returns List Object with access tokens
    """
    Retrieves distinct Plaid access tokens from the local database.
    """
    try:
        db = db_conn()
        if not db:
            return []

        cur = db.cursor()
        # Decrypt the access token using pgp_sym_decrypt
        query = """
            SELECT DISTINCT 
                pgp_sym_decrypt(plaid_access_token::bytea, %s) AS decrypted_access_token
            FROM accounts;
        """
        print(query)
        cur.execute(query, (str(POSTGRES_ENCRYPTION_KEY),))
        tokens = cur.fetchall()
        cur.close()
        db.close()
        print(f"Found {len(tokens)} accounts and their access tokens.")
        return tokens
    except Exception as e:
        print(f"There was an error in get_stored_public_access_tokens():\n{e}")
        return []

def insert_account_df(
    access_token: str,  # The Plaid access token for the account
    accounts_response: dict,  # The response from the Plaid API containing account information
    email: str, # The user email
    phone: str, # The phone number associated with user
) -> None:
    """
    Inserts account information and the associated access token into the database.
    """
    try:
        accounts_df = get_account_df(accounts_response['accounts'])
        db = db_conn()
        if not db:
            return

        cur = db.cursor()
        for _, account in accounts_df.iterrows():
            cur.execute("""
                INSERT INTO accounts (
                    account_id, 
                    mask,
                    name,
                    official_name,
                    persistent_account_id,
                    subtype,
                    type,
                    user_email,
                    user_phone,
                    plaid_access_token
                ) 
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, pgp_sym_encrypt(%s::text, %s)
                )
                ON CONFLICT (account_id) 
                DO UPDATE SET
                    mask = EXCLUDED.mask,
                    name = EXCLUDED.name,
                    official_name = EXCLUDED.official_name,
                    persistent_account_id = EXCLUDED.persistent_account_id,
                    subtype = EXCLUDED.subtype,
                    type = EXCLUDED.type,
                    user_email = EXCLUDED.user_email,
                    user_phone = EXCLUDED.user_phone,
                    plaid_access_token = pgp_sym_encrypt(EXCLUDED.plaid_access_token::text, %s);
            """, (
                account['account_id'],
                account['mask'],
                account['name'],
                account['official_name'],
                account['persistent_account_id'],
                account['subtype'],
                account['type'],
                email,
                phone,
                access_token,
                POSTGRES_ENCRYPTION_KEY,
                POSTGRES_ENCRYPTION_KEY
            ))

        db.commit()
        cur.close()
        db.close()
        print(f"Successfully updated {accounts_df.shape[0]} accounts into the database.")
    except Exception as e:
        print(f"There was an error in insert_account_df():\n{e}")


def insert_transactions_df(
    transactions_df: pd.DataFrame  # A DataFrame containing transaction data
) -> None:
    """
    Inserts transaction data into the database.
    """
    try:
        db = db_conn()
        if not db:
            return

        cur = db.cursor()
        for _, transaction in transactions_df.iterrows():
            cur.execute("""
                INSERT INTO transactions (
                    transaction_id,
                    account_id,
                    amount,
                    authorized_date,
                    category_id,
                    date,
                    iso_currency_code,
                    logo_url,
                    merchant_entity_id,
                    merchant_name,
                    name,
                    payment_channel,
                    pending,
                    personal_finance_category_icon_url,
                    website,
                    personal_finance_category_detailed,
                    personal_finance_category
                ) 
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (transaction_id) 
                DO UPDATE SET
                    account_id = EXCLUDED.account_id,
                    amount = EXCLUDED.amount,
                    authorized_date = EXCLUDED.authorized_date,
                    category_id = EXCLUDED.category_id,
                    date = EXCLUDED.date,
                    iso_currency_code = EXCLUDED.iso_currency_code,
                    logo_url = EXCLUDED.logo_url,
                    merchant_entity_id = EXCLUDED.merchant_entity_id,
                    merchant_name = EXCLUDED.merchant_name,
                    name = EXCLUDED.name,
                    payment_channel = EXCLUDED.payment_channel,
                    pending = EXCLUDED.pending,
                    personal_finance_category_icon_url = EXCLUDED.personal_finance_category_icon_url,
                    website = EXCLUDED.website,
                    personal_finance_category_detailed = EXCLUDED.personal_finance_category_detailed,
                    personal_finance_category = EXCLUDED.personal_finance_category;
            """, (
                transaction['transaction_id'],
                transaction['account_id'],
                transaction['amount'],
                transaction['authorized_date'] if pd.notnull(transaction['authorized_date']) else None,
                transaction['category_id'],
                transaction['date'],
                transaction['iso_currency_code'],
                transaction['logo_url'] if pd.notnull(transaction['logo_url']) else None,
                transaction['merchant_entity_id'] if pd.notnull(transaction['merchant_entity_id']) else None,
                transaction['merchant_name'] if pd.notnull(transaction['merchant_name']) else None,
                transaction['name'],
                transaction['payment_channel'],
                transaction['pending'],
                transaction['personal_finance_category_icon_url'] if pd.notnull(transaction['personal_finance_category_icon_url']) else None,
                transaction['website'] if pd.notnull(transaction['website']) else None,
                transaction['personal_finance_category.detailed'],
                transaction['personal_finance_category.primary']
            ))

        db.commit()
        cur.close()
        db.close()
        print(f"Successfully inserted {transactions_df.shape[0]} transactions into the database.")
    except Exception as e:
        print(f"There was an error in insert_transactions_df():\n{e}")


def upsert_account_balances_df(
    accounts_df: pd.DataFrame  # A DataFrame containing account balance data
) -> None:
    """
    Inserts or updates account balance history in the database.
    """
    try:
        db = db_conn()
        if not db:
            return

        cur = db.cursor()
        for _, account in accounts_df.iterrows():
            cur.execute("""
                INSERT INTO accounts_balance_history (
                    account_id, 
                    balances_available,
                    balances_current,
                    balances_iso_currency_code,
                    balances_limit,
                    balances_unofficial_currency_code,
                    balances_datetime
                ) 
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                );
            """, (
                account['account_id'],
                account['balances_available'],
                account['balances_current'],
                account['balances_iso_currency_code'],
                account['balances_limit'],
                account['balances_unofficial_currency_code'],
                datetime.datetime.now(),
            ))

        db.commit()
        cur.close()
        db.close()
        print(f"Successfully updated {accounts_df.shape[0]} account balances into the database.")
    except Exception as e:
        print(f"There was an error in upsert_account_balances_df():\n{e}")


# %% ../nbs/core.ipynb 12
def generate_link_token(
    email: str,  # The user's email address
    phone: str   # The user's phone number
) -> Optional[str]:  # Returns the generated link token if successful, otherwise None
    """
    Generates a link token to authenticate with the Plaid API.
    """
    try:
        payload = {
            "client_id": PLAID_CLIENT_ID,
            "secret": PLAID_SECRET,
            "client_name": "Jupyter Notebook",
            "country_codes": PLAID_COUNTRY_CODES,
            "language": "en",
            "user": {
                "client_user_id": str(uuid.uuid4()),
                "phone_number": phone,
                "email_address": email,
            },
            "hosted_link": {},
            "products": PLAID_PRODUCTS,
        }
        link_token_response = plaid_post("link/token/create", payload)

        print(
            f"Navigate to this page and authenticate with your bank: "
            f"{link_token_response.get('hosted_link_url', 'No URL provided')}"
        )
        print(
            f"This link expires: {link_token_response.get('expiration', 'No expiration provided')}"
        )

        return link_token_response.get("link_token")

    except Exception as e:
        print(f"There was an error in generate_link_token:\n{e}")
        return None


def get_and_save_public_token(
    link_token: str, # The link token generated during the Plaid Link flow
    email: str,  # The user's email address
    phone: str   # The user's phone number
) -> None:
    """
    Retrieves a public token using the link token, exchanges it for an access token, 
    and saves the account information to the database.
    """
    exchange_response = ''
    access_token = ''

    try:
        payload = {
            "client_id": PLAID_CLIENT_ID,
            "secret": PLAID_SECRET,
            "link_token": link_token,
        }
        link_token_details = plaid_post("link/token/get", payload)

        public_token = (
            link_token_details['link_sessions'][0]['results']['item_add_results'][0]['public_token']
        )

        payload = {
            "client_id": PLAID_CLIENT_ID,
            "secret": PLAID_SECRET,
            "public_token": public_token,
        }
        exchange_response = plaid_post("item/public_token/exchange", payload)
        access_token = exchange_response.get("access_token")

        if access_token:
            print("Access token has been generated successfully")
        else:
            print("Failed to generate access token.")
            return

    except KeyError as ke:
        print(f"Key error occurred in get_and_save_public_token: Missing key {ke}")
        return
    except Exception as e:
        print(f"There was an error in get_and_save_public_token:\n{e}\nResponse: {exchange_response}")
        return

    try:
        accounts_response = get_account(access_token)
        insert_account_df(access_token, accounts_response, email, phone)
    except Exception as e:
        print(f"There was an error while saving account information:\n{e}")


# %% ../nbs/core.ipynb 14
def get_and_save_all_account_transactions() -> None:
    """
    Retrieves all account transactions for stored public access tokens
    and inserts the transactions into the database.

    Steps:

    * Fetch public access tokens from the database.
    * Retrieve transactions data for each account associated with the tokens. 
    * Insert the retrieved transactions into the database.

    Returns:
        None
    """
    try:
        # Step 1: Fetch public access tokens
        access_tokens = get_stored_public_access_tokens()

        # Step 2: Retrieve all transactions as a DataFrame
        transactions_df = get_transactions_df(access_tokens)

        # Step 3: Insert transactions into the database
        insert_transactions_df(transactions_df)
        print("Successfully retrieved and saved all account transactions.")

    except Exception as e:
        print(f"An error occurred in get_and_save_all_account_transactions:\n{e}")


def get_and_save_balance_history() -> None:
    """
    Retrieves account balance history for stored public access tokens
    and updates the balance history in the database.

    Steps:
    
    * Fetch public access tokens from the database.
    * Retrieve account details for each account associated with the tokens. 
    * Update the account balance history in the database. 
    Returns:
        None
    """
    try:
        # Step 1: Fetch public access tokens
        access_tokens = get_stored_public_access_tokens()

        # Step 2: Retrieve all account details as a DataFrame
        accounts_df = get_accounts_df(access_tokens)

        # Step 3: Update account balance history in the database
        upsert_account_balances_df(accounts_df)
        print("Successfully retrieved and saved account balance history.")

    except Exception as e:
        print(f"An error occurred in get_and_save_balance_history:\n{e}")


# %% ../nbs/core.ipynb 15
def about():
    """
    Print environmental details for this instance of `jupyter-finance`
    """
    print("="*60)
    print("="*60)
    print(f"Jupyter Finances")
    print(f"Current Date and Time: {datetime.now()}")
    
    print("="*60)
    print(f"Plaid API ({PLAID_ENV})")
    print("="*60)
    print(f"PLAID_CLIENT_ID: {PLAID_CLIENT_ID}")
    print(f"PLAID_PRODUCTS: {PLAID_PRODUCTS}")
    print(f"PLAID_COUNTRY_CODES: {PLAID_COUNTRY_CODES}")
    print("="*60)

