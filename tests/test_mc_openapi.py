from mc_openapi import __version__
from mc_openapi.doml_mc.common_reqs import CommonRequirements
import requests


def test_version():
    assert __version__ == '1.1.0'


def test_post_nginx_sat():
    with open("tests/doml/nginx-openstack_v2.0.domlx", "r") as f:
        doml = f.read()

    r = requests.post("http://0.0.0.0:8080/modelcheck", data=doml)
    payload = r.json()
    assert r.status_code == requests.codes.ok
    assert payload["result"] is not None
    assert payload["result"] == "sat"


def test_post_faas_sat():
    with open("tests/doml/faas.domlx", "r") as f:
        doml = f.read()

    r = requests.post("http://0.0.0.0:8080/modelcheck", data=doml)
    payload = r.json()
    assert r.status_code == requests.codes.ok
    assert payload["result"] is not None
    assert payload["result"] == "unsat"


def test_post_common_reqs():
    for req in CommonRequirements.get_all_requirements():
        with open(f"tests/doml/nginx-openstack_v2.0_wrong_{req.assert_name}.domlx", "r") as f:
            doml = f.read()

        r = requests.post("http://0.0.0.0:8080/modelcheck", data=doml)
        payload = r.json()
        assert r.status_code == requests.codes.ok
        assert payload["result"] is not None
        assert payload["result"] == "unsat"
        assert req.error_description in payload["description"]
