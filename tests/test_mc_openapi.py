from mc_openapi import __version__
import requests
import json

def test_version():
    assert __version__ == '0.1.0'

def test_post_sat():
    with open("tests/doml/POSIDONIA.doml", "r") as f:
        doml = json.load(f)

    r = requests.post("http://0.0.0.0:8080/modelcheck", json={'model': doml})
    payload = r.json()
    assert r.status_code == requests.codes.ok
    assert payload["result"] is not None
    assert payload["result"] == "sat"

def test_post_unsat():
    with open("tests/doml/POSIDONIA_wrong.doml", "r") as f:
        doml = json.load(f)

    r = requests.post("http://0.0.0.0:8080/modelcheck", json={'model': doml})
    payload = r.json()
    assert r.status_code == requests.codes.ok
    assert payload["result"] is not None
    assert payload["result"] == "unsat"
