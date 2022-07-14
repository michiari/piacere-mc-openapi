REST APIs
=========

The `OpenAPI`_ definition of the REST APIs is in ``mc_openapi/openapi/model_checker.yaml``.

The APIs can also be browsed with `Swagger UI`_ by appending ``/ui/`` to the APIs' HTTP address.

For APIs usage examples, you may look into the tests, in ``tests/test_mc_openapi.py``.
Some DOML examples in XMI format are sent to the server.
One of them is correct (``tests/doml/nginx-openstack_v2.domlx``),
and the server answers with ``"sat"`` (meaning the requirements are satisfied),
and the other one contains an error (``tests/doml/nginx-openstack_v2_wrong.domlx``),
so the server answers with ``"unsat"``.


.. _OpenAPI: https://www.openapis.org/
.. _Swagger UI: https://swagger.io/tools/swagger-ui/
