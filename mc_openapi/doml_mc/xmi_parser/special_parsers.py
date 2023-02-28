from ipaddress import ip_address, ip_network

from .ecore import SpecialParser
from ..intermediate_model.metamodel import DOMLVersion, MetaModels
from ..intermediate_model.doml_element import Attributes


SpecialParsers: dict[DOMLVersion, SpecialParser] = {}


def parse_network_address_range(arange: str) -> Attributes:
    ipnet = ip_network(arange)
    return {"address_lb": [int(ipnet[0])], "address_ub": [int(ipnet[-1])]}


def parse_iface_address(addrport: str) -> Attributes:
    addr, _, port = addrport.rpartition(":")
    if addr == "":
        addr = port
    return {"endPoint": [int(ip_address(addr))]}


def parse_memory_mb(mem: str) -> Attributes:
    return {"memory_mb":  [int(mem)], "memory_kb": [int(mem * 1024)]}


def parse_fproperty(fval: str) -> Attributes:
    return {"value": [str(fval)]}


def parse_cidr(arange: str) -> Attributes:
    attrs: Attributes = {"addressRange": [arange]}
    if arange[0] == "/":
        try:
            attrs["cidr"] = [int(arange[1:])]
        except (ValueError, IndexError):
            pass
    return attrs


def init_special_parsers():
    global SpecialParsers
    assert len(MetaModels) > 0

    attribute_parsers = {
        DOMLVersion.V1_0: {
            ("infrastructure_Network", "addressRange"): parse_network_address_range,
            ("infrastructure_NetworkInterface", "endPoint"): parse_iface_address,
            ("commons_FProperty", "value"): parse_fproperty,
        },
        DOMLVersion.V2_0: {
            ("infrastructure_Network", "addressRange"): parse_network_address_range,
            ("infrastructure_NetworkInterface", "endPoint"): parse_iface_address,
            ("infrastructure_ComputingNode", "memory_mb"): parse_memory_mb,
            ("commons_FProperty", "value"): parse_fproperty,
        },
        DOMLVersion.V2_1: {
            ("infrastructure_Network", "addressRange"): parse_cidr,
            ("infrastructure_NetworkInterface", "endPoint"): parse_iface_address,
            ("infrastructure_ComputingNode", "memory_mb"): parse_memory_mb,
            ("commons_FProperty", "value"): parse_fproperty,
        },
        DOMLVersion.V2_2: {
            ("infrastructure_Network", "addressRange"): parse_cidr,
            ("infrastructure_NetworkInterface", "endPoint"): parse_iface_address,
            ("infrastructure_ComputingNode", "memory_mb"): parse_memory_mb,
            ("commons_FProperty", "value"): parse_fproperty,
        },
    }
    for ver in DOMLVersion:
        SpecialParsers[ver] = SpecialParser(MetaModels[ver], attribute_parsers[ver])
