"""Test-suite bootstrap.

`src/app.py` deliberately refuses to import without SECRET_KEY — a missing
value must fail the deploy rather than silently ship a guessable key. That
makes a bare `pytest` fail at collection for any module that imports the app at
module scope, which is a confusing first experience for the next person. Set a
throwaway key for tests only; a real environment always overrides it.
"""
import os

os.environ.setdefault("SECRET_KEY", "test")
