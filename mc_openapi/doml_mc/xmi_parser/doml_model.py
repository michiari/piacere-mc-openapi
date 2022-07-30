import copy
import importlib.resources as ilres
from ipaddress import ip_address, ip_network

from mc_openapi import assets
from mc_openapi.bytes_uri import BytesURI
from pyecore.ecore import EObject
from pyecore.resources import ResourceSet

from ..intermediate_model.doml_element import Attributes, IntermediateModel
from ..intermediate_model.metamodel import MetaModel
from .ecore import ELayerParser, SpecialParser


doml_rset = None
def init_doml_rset():  # noqa: E302
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
    rset = get_rset()
    doml_uri = BytesURI("user_doml", bytes=raw_model)
    resource = rset.create_resource(doml_uri)
    resource.load()
    return resource.contents[0]


def check_domlx_version(model: EObject):
    if hasattr(model, "version") and model.version != "v2":
        raise RuntimeError(f"Supplied with DOMLX model of unsupported version {model.version} (supported version is v2).")


def parse_doml_model(raw_model: bytes, mm: MetaModel) -> IntermediateModel:
    def parse_network_address_range(arange: str) -> Attributes:
        ipnet = ip_network(arange)
        return {"address_lb": [int(ipnet[0])], "address_ub": [int(ipnet[-1])]}

    model = parse_xmi_model(raw_model)
    check_domlx_version(model)

    sp = SpecialParser(mm, {
        ("infrastructure_Network", "addressRange"): parse_network_address_range,
        ("infrastructure_NetworkInterface", "endPoint"): lambda addr: {"endPoint": [int(ip_address(addr))]},
        ("infrastructure_ComputingNode", "memory_mb"): lambda mem: {"memory_mb":  [int(mem)], "memory_kb": [int(mem * 1024)]}
    })
    elp = ELayerParser(mm, sp)
    elp.parse_elayer(model.application)
    elp.parse_elayer(model.infrastructure)
    elp.parse_elayer(model.activeConfiguration)
    im = elp.parse_elayer(model.activeInfrastructure)

    return im
