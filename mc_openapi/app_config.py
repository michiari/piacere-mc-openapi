import connexion

app = connexion.App(__name__, specification_dir='openapi/')
app.add_api('model_checker.yaml')

application = app.app
