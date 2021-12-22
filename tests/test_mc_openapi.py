from mc_openapi import __version__
import requests

def test_version():
    assert __version__ == '0.1.0'

def test_post():
    r = requests.post("http://0.0.0.0:8080/modelcheck", json={'model': {'sbirio': 'frosco'}})
    payload = r.json()
    assert r.status_code == requests.codes.ok
    assert payload["result"] is not None
