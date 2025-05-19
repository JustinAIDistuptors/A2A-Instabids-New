# src/instabids/__init__.py
# This file can be largely empty if submodules are imported directly where needed,
# or it can pre-import key submodules for the package.

print("DEBUG: instabids package __init__.py executed") # Optional debug for one last check

from . import data_access
from . import memory
# Example: you might also have:
# from . import agents
# from . import webhooks

print("DEBUG: instabids package basic imports completed.")
