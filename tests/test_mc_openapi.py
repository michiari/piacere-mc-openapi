from mc_openapi import __version__
import requests


def test_version():
    assert __version__ == '0.2.0'


def test_post_sat():
    with open("tests/doml/nginx-openstack_v2.domlx", "r") as f:
        doml = f.read()

    r = requests.post("http://0.0.0.0:8080/modelcheck", data=doml)
    payload = r.json()
    assert r.status_code == requests.codes.ok
    assert payload["result"] is not None
    assert payload["result"] == "sat"


def test_post_unsat():
    with open("tests/doml/nginx-openstack_v2_wrong.domlx", "r") as f:
        doml = f.read()

    r = requests.post("http://0.0.0.0:8080/modelcheck", data=doml)
    payload = r.json()
    assert r.status_code == requests.codes.ok
    assert payload["result"] is not None
    assert payload["result"] == "unsat"
