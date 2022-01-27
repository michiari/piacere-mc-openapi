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

## Run with Docker

First, build the docker image with the usual
```sh
$ docker build -t wp4/dmc .
```
And then run it with
```sh
$ docker run -d wp4/dmc
```
The uWSGI server will be running and listening on port 80 of the container.


## REST APIs

The OpenAPI definition of the REST APIs is in `mc_openapi/openapi/model_checker.yaml`.

The APIs can also be browsed with [Swagger UI](https://swagger.io/tools/swagger-ui/) by appending `/ui/` to the API HTTP address.

For APIs usage examples, you may look into the tests, in `tests/test_mc_openapi.py`.
Two DOML examples in JSON format are sent to the server.
One of them is correct (`tests/doml/POSIDONIA.doml`), and the server answers with `"sat"` (meaning the requirements are satisfied), and the other one contains an error (`tests/doml/POSIDONIA_wrong.doml`), so the server answers with `"unsat"`.

**Note:** for the time being, the `model` field of the POST request's body accepts any JSON object. This will be changed to the DOML JSON schema when available.
