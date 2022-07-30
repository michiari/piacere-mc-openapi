# PIACERE Model Checker

The DOML Model Checker is a component of the [PIACERE](https://www.piacere-project.eu/) framework
in charge of checking the correctness and consistency of
[DOML](https://www.piacere-doml.deib.polimi.it/) models.

This project is packaged with [Poetry](https://python-poetry.org/).


## Build and Run

Build with
```sh
poetry install
```
then run with
```sh
poetry run python -m mc_openapi
```

Run tests with:
```sh
poetry run python -m pytest
```


## Run with uWSGI

The project may be run with [uWSGI](https://uwsgi-docs.readthedocs.io/) as follows:
```sh
uwsgi --http :8080 --yaml uwsgi_config.yaml
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
The uWSGI server will be running and listening on port 80 of the container.


## Building the Documentation

The documentation has been written in [Sphinx](https://www.sphinx-doc.org/)
and covers both usage through the PIACERE IDE and the REST APIs.

To build it, type
```sh
poetry shell
```
and then
```sh
cd docs
make html
```

The documentation will be generated in `docs/_build`.
