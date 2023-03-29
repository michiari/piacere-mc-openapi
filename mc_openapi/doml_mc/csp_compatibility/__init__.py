from .allowlist_check_v1 import CSPCompatibilityValidator
import importlib.resources as ilres
from ... import assets
import yaml

FILE = lambda filename: ilres.files(assets).joinpath(f"csp/{filename}")

SOURCES = [
    'keypair',
    'arch',
    'os',
    'minimum_setup'
]

DATA = {}

for src in SOURCES:
    with open(FILE(f'{src}.yml')) as data:
        DATA[src] = yaml.safe_load(data)

CSPCompatibilityValidator = CSPCompatibilityValidator(DATA)

