# PIACERE Model Checker REST API server

This project is packaged with [Poetry](https://python-poetry.org/).

## Build and Run

Build with
```sh
$ poetry install
```
then run with
```sh
$ poetry run python -m mc_openapi
```

Run tests with:
```sh
$ poetry run python -m pytest
```

## Run with uWSGI

The project may be run with [uWSGI](https://uwsgi-docs.readthedocs.io/) as follows:
```sh
$ uwsgi --http :8080 -w mc_openapi.app_config -p 4
```
