# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_first_time.ipynb.

# %% auto 0
__all__ = ['email', 'phone', 'link_token', 'access_tokens']

# %% ../nbs/00_first_time.ipynb 2
import os
from .core import *


# %% ../nbs/00_first_time.ipynb 5
email = os.getenv("USER_EMAIL", "default@email.com")
phone = os.getenv("USER_PHONE", "+1 000 0000000")


# %% ../nbs/00_first_time.ipynb 7
link_token = generate_link_token(email, phone)

# %% ../nbs/00_first_time.ipynb 9
get_and_save_public_token(link_token)

# %% ../nbs/00_first_time.ipynb 11
access_tokens = get_stored_public_access_tokens()
get_and_save_all_account_transactions()

