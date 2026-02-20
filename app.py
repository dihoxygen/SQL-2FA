from flask import Flask, render_template
from config import SECRET_KEY # imports secret key from config
from routes.requests import requests_bp

# instance of Flask
app = Flask(__name__)
app.secret_key = SECRET_KEY

app.register_blueprint(requests_bp)

@app.route('/')
def index():
    return render_template("index.html")

if __name__ == '__main__':
    app.run()
