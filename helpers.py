# helpers.py
# Shared utilities used across multiple blueprint files.
# Anything that more than one route file needs should live here.

from functools import wraps  # wraps preserves the original function's name/docstring
from flask import session, redirect, url_for


def login_required(f):
    """
    A decorator that protects routes so only logged-in users can access them.


    What this does:
      1. Checks if 'operator_id' exists in the session (set during login).
      2. If NOT logged in -> redirect to the login page.
      3. If logged in -> call the original route function normally.
    """
    @wraps(f)  # This makes decorated_function "look like" f to Flask
    def decorated_function(*args, **kwargs):
        # *args and **kwargs capture any arguments the route might receive
        # (like request_id in /requests/<request_id>)
        if 'operator_id' not in session:
            return redirect(url_for('index'))  # 'index' is the login page route name
        return f(*args, **kwargs)  # User is logged in, run the actual route
    return decorated_function
