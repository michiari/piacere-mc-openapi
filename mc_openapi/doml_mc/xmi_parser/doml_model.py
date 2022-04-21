import copy
import importlib.resources as ilres

from mc_openapi import assets
from mc_openapi.bytes_uri import BytesURI
from pyecore.ecore import EObject
from pyecore.resources import ResourceSet

from ..intermediate_model.metamodel import MetaModel
from ..model.doml_model import DOMLModel
from .application import parse_application
from .concretization import parse_concretization
from .infrastructure import parse_infrastructure
from .optimization import parse_optimization

doml_rset = None
def init_doml_rset():
    global doml_rset
    rset = ResourceSet()
    resource = rset.get_resource(BytesURI(
        "doml", bytes=ilres.read_binary(assets, "doml.ecore")
    ))
    doml_metamodel = resource.contents[0]

    rset.metamodel_registry[doml_metamodel.nsURI] = doml_metamodel
    for subp in doml_metamodel.eSubpackages:
        rset.metamodel_registry[subp.nsURI] = subp

    doml_rset = rset


def get_rset():
    assert doml_rset is not None
    return copy.copy(doml_rset)


def parse_xmi_model(raw_model: bytes) -> EObject:
    try:
        rset = get_rset()
        doml_uri = BytesURI("user_doml", bytes=raw_model)
        resource = rset.create_resource(doml_uri)
        resource.load()
        return resource.contents[0]

    except Exception:
        # TODO: do something meaningful
        raise


def parse_doml_model(raw_model: bytes, mm: MetaModel) -> DOMLModel:
    model = parse_xmi_model(raw_model)

    return DOMLModel(
        name=model.name,
        description=model.description,
        application=parse_application(model.application),
        infrastructure=parse_infrastructure(model.infrastructure, mm),
        optimization=parse_optimization(model.optimization)
        if model.optimization is not None else None,
        concretizations={
            concdoc.name: parse_concretization(concdoc)
            for concdoc in model.concretizations
        },
    )
