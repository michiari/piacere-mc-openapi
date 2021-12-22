# PIACERE Model Checker REST API server

Thys project is packaged with Poetry.

## Build and Run

Build with
```
$ poetry install
```
then run with
```
poetry run python -m mc_openapi
```

Run tests with:
```
$ poetry run python -m pytest
```

## Run with uWSGI

The project may be run with uWSGI as follows:
```
$ uwsgi --http :8080 -w mc_openapi.app_config -p 4
```
