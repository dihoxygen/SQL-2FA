# routes/auth.py
# Handles login and logout -- the first thing any user interacts with.

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import text
from db import sql2fa_engine

# Create the auth blueprint. Flask uses the name 'auth' internally,
# so later you'd reference routes as url_for('auth.login'), url_for('auth.logout').
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    GET  /login -> Show the login form (login.html).
    POST /login -> User submitted the form. Validate credentials.

    Flow:
      1. Read the operator_id and password from the form.
      2. Call the plpgsql function verify_operator_password().
         That function uses bcrypt internally (crypt + gen_salt)
         and returns TRUE or FALSE.
      3. If TRUE  -> store operator_id in session, redirect to dashboard.
      4. If FALSE -> show an error message, send them back to login.
    """
    if request.method == 'POST':
        # request.form is a dictionary of everything the <form> submitted.
        # The keys ('username', 'password') must match the "name" attributes
        # on your <input> elements in the HTML form.
        operator_id = request.form['username']
        password = request.form['password']

        with sql2fa_engine.connect() as conn:
            # :op_id and :pw are named placeholders.
            # SQLAlchemy safely substitutes the values from the dict,
            # preventing SQL injection (where someone types malicious SQL
            # into the form field).
            result = conn.execute(
                text("SELECT sql2fa.verify_operator_password(:op_id, :pw)"),
                {"op_id": operator_id, "pw": password},
            )
            # .scalar() returns the single value from a single-row, single-column result.
            # In this case, it's the boolean TRUE or FALSE from the plpgsql function.
            is_valid = result.scalar()

        if is_valid:
            # SUCCESS: Store the operator_id in the session.
            # This is the moment the "locker" gets filled.
            # From now on, every request from this browser carries this value
            # in a signed cookie. The login_required decorator reads it.
            session['operator_id'] = operator_id
            return redirect(url_for('dashboard.home'))
        else:
            # FAILURE: flash() stores a one-time message that survives the redirect.
            # The template can display it using get_flashed_messages().
            # The second argument ('error') is a category you can use for styling.
            flash('Invalid operator ID or password.', 'error')
            return redirect(url_for('auth.login'))

    # GET request: just show the login form
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    GET  /register -> Show the registration form.
    POST /register -> Create the operator and set their password.

    Two-step process:
      1. INSERT a new row into sql2fa."OPERATOR" with the operator_id.
         This creates the user but with no password yet (password_hash is NULL).
      2. Call create_operator_password() to hash and store the password.
         This function does an UPDATE on the row we just created.

    We also confirm the password by requiring the user to type it twice.
    Python checks that they match BEFORE touching the database.
    """
    if request.method == 'POST':
        operator_id = request.form['operator_id'].strip().upper()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Validate: passwords must match
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.register'))

        # Validate: operator_id must be exactly 4 characters (char(4) in DB)
        if len(operator_id) != 4:
            flash('Operator ID must be exactly 4 characters.', 'error')
            return redirect(url_for('auth.register'))

        try:
            with sql2fa_engine.connect() as conn:
                # Step 1: Create the operator row.
                # If the operator_id already exists, the database will raise
                # a unique constraint violation, which the except block catches.
                conn.execute(
                    text('INSERT INTO sql2fa."OPERATOR" (operator_id) VALUES (:op_id)'),
                    {"op_id": operator_id},
                )

                # Step 2: Set the password using your plpgsql function.
                # create_operator_password does:
                #   UPDATE sql2fa."OPERATOR"
                #   SET password_hash = crypt(plain_txt, gen_salt('bf', 12))
                #   WHERE operator_id = op_id
                conn.execute(
                    text("SELECT sql2fa.create_operator_password(:op_id, :pw)"),
                    {"op_id": operator_id, "pw": password},
                )
                conn.commit()

            flash('Account created! You can now log in.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            # Most likely cause: operator_id already exists (unique constraint).
            # str(e) contains the database error message.
            flash(f'Could not create account: {e}', 'error')
            return redirect(url_for('auth.register'))

    return render_template('register.html')


@auth_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """
    Lets a logged-in user change their own password.

    Security: requires the OLD password before accepting a new one.
    This prevents someone from changing your password if you left
    your browser open and walked away.

    Flow:
      1. Verify the old password using verify_operator_password().
      2. If valid, set the new password using create_operator_password().
      3. If old password is wrong, show an error.
    """
    # Must be logged in to change password
    if 'operator_id' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        operator_id = session['operator_id']
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('auth.change_password'))

        with sql2fa_engine.connect() as conn:
            # Step 1: Verify the old password first
            result = conn.execute(
                text("SELECT sql2fa.verify_operator_password(:op_id, :pw)"),
                {"op_id": operator_id, "pw": old_password},
            )
            is_valid = result.scalar()

            if not is_valid:
                flash('Current password is incorrect.', 'error')
                return redirect(url_for('auth.change_password'))

            # Step 2: Old password was correct -- set the new one.
            # create_operator_password overwrites the existing hash
            # with a new bcrypt hash of the new password.
            conn.execute(
                text("SELECT sql2fa.create_operator_password(:op_id, :pw)"),
                {"op_id": operator_id, "pw": new_password},
            )
            conn.commit()

        flash('Password changed successfully.', 'success')
        return redirect(url_for('dashboard.home'))

    return render_template('change_password.html')


@auth_bp.route('/logout')
def logout():
    """
    Clears everything from the session (removes the operator_id),
    then sends the user back to the login page.
    After this, login_required will block them from all protected pages.
    """
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
