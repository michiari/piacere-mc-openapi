# PIACERE Model Checker
_______________________
## **You can read the [docs here](https://andreafranchini.com/piacere-model-checker/) for more details.**
_______________________

The DOML Model Checker is a component of the [PIACERE](https://www.piacere-project.eu/) framework
in charge of checking the correctness and consistency of
[DOML](https://www.piacere-doml.deib.polimi.it/) models.


 We provide a `requirements.txt` file for CI/CD purposes.

 If you add a new package, regenerate it by running:
 
 ```sh
 poetry run pip freeze > requirements.txt
 ```

## Setup

Activate the Python Virtual Environment with:
```sh
source .venv/bin/activate
```
Install the required packages with:
```sh
pip install -r requirements.txt
```

## Run the model checker web server
```sh
python -m mc_openapi
```

## Run with Uvicorn

The project may be run with [Uvicorn](https://www.uvicorn.org/) as follows:
```sh
uvicorn --port 8080 --host 0.0.0.0 --interface wsgi --workers 2 mc_openapi.app_config:app
```
## Run tests

Run tests with:
```sh
python -m pytest
```


## Run with Docker

First, build the docker image with the usual
```sh
docker build -t wp4/dmc .
```
And then run it with
```sh
docker run -d wp4/dmc
```
The Uvicorn server will be running and listening on port 80 of the container.
To use it locally, you may e.g. bind it with port 8080 of `localhost`
by adding `-p 127.0.0.1:8080:80/tcp` to the `docker run` command.


## Building the Documentation

The documentation has been written in [Sphinx](https://www.sphinx-doc.org/)
and covers both usage through the PIACERE IDE and the REST APIs.

Build the documentation with:
```sh
cd docs
make html
```

The documentation will be generated in `docs/_build`.
