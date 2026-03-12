# app.py
# This is the entry point of the application.
# It creates the Flask app, configures it, and registers all the blueprints.
# When you run "flask run" or "python app.py", this is the file that starts everything.

from flask import Flask, render_template
from config import SECRET_KEY

# Import each blueprint from the routes/ package.
# Each blueprint is a separate file with its own set of routes.
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.requests import requests_bp
from routes.open_requests import open_requests_bp
from routes.approvals import approvals_bp
from routes.manager import manager_bp
from routes.query_tool import query_tool_bp

app = Flask(__name__)

# secret_key is used to sign the session cookie.
# Without it, Flask sessions won't work and you'll get an error.
# This should be a long random string in production (never commit the real one).
app.secret_key = SECRET_KEY

# register_blueprint() tells Flask: "add all the routes from this blueprint
# to the app." The order doesn't matter -- Flask matches URLs by specificity,
# not by registration order.
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(requests_bp)
app.register_blueprint(open_requests_bp)
app.register_blueprint(approvals_bp)
app.register_blueprint(manager_bp)
app.register_blueprint(query_tool_bp)


@app.route('/')
def index():
    """
    The root URL redirects to the login page.
    This is the only route defined directly in app.py.
    Everything else lives in the blueprint files.
    """
    return render_template("login.html")


if __name__ == '__main__':
    app.run()
