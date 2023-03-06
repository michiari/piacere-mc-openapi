from .validator import CSPCompatibilityValidator
import importlib.resources as ilres
from ... import assets
import yaml

FILE = lambda filename: ilres.files(assets).joinpath(f"csp/{filename}")

with open(FILE('keypairs.yml')) as kp:
    KEYPAIRS = yaml.safe_load(kp)

with open(FILE('architectures.yml')) as kp:
    ARCHS = yaml.safe_load(kp)

with open(FILE('regions.yml')) as kp:
    REGIONS = yaml.safe_load(kp)

CSPCompatibilityValidator = CSPCompatibilityValidator(
    keypairs=KEYPAIRS,
    architectures=ARCHS,
    regions=REGIONS
)

