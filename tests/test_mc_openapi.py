from mc_openapi import __version__
from mc_openapi.doml_mc.common_reqs import CommonRequirements
from mc_openapi.doml_mc import DOMLVersion
import requests


def test_version():
    assert __version__ == '1.2.0'


# V2_0 tests
def test_post_nginx_sat_V2_0():
    with open("tests/doml/v2.0/nginx-openstack_v2.0.domlx", "r") as f:
        doml = f.read()

    r = requests.post("http://0.0.0.0:8080/modelcheck", data=doml)
    payload = r.json()
    assert r.status_code == requests.codes.ok
    assert payload["result"] is not None
    assert payload["result"] == "sat"


def test_post_faas_unsat_V2_0():
    with open("tests/doml/v2.0/faas.domlx", "r") as f:
        doml = f.read()

    r = requests.post("http://0.0.0.0:8080/modelcheck", data=doml)
    payload = r.json()
    assert r.status_code == requests.codes.ok
    assert payload["result"] is not None
    assert payload["result"] == "unsat"


def test_post_common_reqs_V2_0():
    check_strings = [
        "is connected to no network interface.",
        "but they are deployed to nodes that cannot communicate through a common network.",
        "share the same IP address.",
        "is not deployed to any abstract infrastructure node.",
        "has not been mapped to any element in the active concretization.",
        "is mapped to no abstract infrastructure element."
    ]

    for req, err_desc in zip(CommonRequirements[DOMLVersion.V2_0].get_all_requirements(), check_strings):
        with open(f"tests/doml/v2.0/nginx-openstack_v2.0_wrong_{req.assert_name}.domlx", "r") as f:
            doml = f.read()

        r = requests.post("http://0.0.0.0:8080/modelcheck", data=doml)
        payload = r.json()
        assert r.status_code == requests.codes.ok
        assert payload["result"] is not None
        assert payload["result"] == "unsat"
        assert err_desc in payload["description"]


# V2_1 tests
def test_post_nginx_sat_V2_1():
    with open("tests/doml/v2.1/nginx-aws-ec2.domlx", "r") as f:
        doml = f.read()

    r = requests.post("http://0.0.0.0:8080/modelcheck", data=doml)
    payload = r.json()
    assert r.status_code == requests.codes.ok
    assert payload["result"] is not None
    assert payload["result"] == "sat"


def test_post_faas_unsat_V2_1():
    with open("tests/doml/v2.1/faas.domlx", "r") as f:
        doml = f.read()

    r = requests.post("http://0.0.0.0:8080/modelcheck", data=doml)
    payload = r.json()
    assert r.status_code == requests.codes.ok
    assert payload["result"] is not None
    assert payload["result"] == "unsat"
