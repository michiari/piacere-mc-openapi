import connexion
from flask import render_template

app = connexion.App(__name__, specification_dir='openapi/')
app.add_api('model_checker.yaml')

@app.route("/")
def home():
    return render_template('home.html')


application = app.app
