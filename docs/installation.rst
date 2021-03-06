Installation
============

The DOML Model Checker receives user inputs through its REST APIs.
In this guide we illuestrate saveral ways of setting up the server for these APIs.


Build and run locally for testing
---------------------------------

This project is packaged with `Poetry`_, which we assume you have already
`installed <https://python-poetry.org/docs/#installation>`_ into your system.


Build with::

  poetry install

then run with::

  poetry run python -m mc_openapi

this command serves the APIs through a `Flask`_ instance,
which is suitable for testing, but not recommended for production.
You may read the API specification generated by `Swagger-UI`_ by
pointing your browser to http://127.0.0.1:8080/ui/.


Then, run tests with::

  poetry run python -m pytest


Run locally with uWSGI
----------------------

The project may be run with `uWSGI`_,
which is better-suited for production environments, as follows::

  uwsgi --http :8080 -w mc_openapi.app_config -p 4


Run with Docker
---------------

The best way of deploying the DOML Model Checker is by using `Docker`_.

First, build the docker image with the usual::

  docker build -t wp4/dmc .

And then run it with::

  docker run -d wp4/dmc

The uWSGI server will be running and listening on port 80 of the container.


Building the Documentation
--------------------------

The documentation has been written in `Sphinx`_.

To build it, type::

  poetry shell

and then::

  cd docs
  make html

The documentation will be generated in ``docs/_build``.


.. _Poetry: https://python-poetry.org/
.. _Flask: https://flask.palletsprojects.com/
.. _Swagger-UI: https://swagger.io/tools/swagger-ui/
.. _uWSGI: https://uwsgi-docs.readthedocs.io/
.. _Docker: https://www.docker.com/
.. _Sphinx: https://www.sphinx-doc.org/
