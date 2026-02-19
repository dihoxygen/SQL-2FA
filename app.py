from flask import Flask, render_template
from db import engine

# Generate the app instance of Flask
app = Flask(__name__)

@app.route('/')
def index():
    return render_template("index.html")

if __name__ == '__main__':
    app.run()
