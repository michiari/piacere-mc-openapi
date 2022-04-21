from dataclasses import dataclass

from ..intermediate_model.doml_element import parse_attrs_and_assocs_from_doc
from ..intermediate_model.metamodel import MetaModel
from .types import Associations, Attributes


@dataclass
class Infrastructure:
    nodes: dict[str, "InfrastructureNode"]
    networks: dict[str, "Network"]
    groups: dict[str, "Group"]


@dataclass
class InfrastructureNode:
    name: str
    typeId: str
    network_interfaces: dict[str, "NetworkInterface"]
    attributes: Attributes
    associations: Associations


@dataclass
class Network:
    name: str
    protocol: str
    addressRange: str


@dataclass
class NetworkInterface:
    name: str
    belongsTo: str
    endPoint: str


@dataclass
class Group:
    name: str
    typeId: str


def parse_infrastructure(doc: dict, mm: MetaModel) -> Infrastructure:
    def parse_infrastructure_node(doc: dict) -> InfrastructureNode:
        def parse_network_interface(doc: dict) -> NetworkInterface:
            return NetworkInterface(
                name=doc["name"],
                belongsTo=doc["belongsTo"],
                endPoint=doc["endPoint"],
            )

        typeId = doc["typeId"]
        attrs, assocs = parse_attrs_and_assocs_from_doc(doc, typeId, mm)
        return InfrastructureNode(
            name=doc["name"],
            typeId=typeId,
            network_interfaces={
                niface_doc["name"]: parse_network_interface(niface_doc)
                for niface_doc in doc.get("interfaces", [])
            },
            attributes=attrs,
            associations=assocs,
        )

    def parse_network(doc: dict) -> Network:
        return Network(
            name=doc["name"],
            protocol=doc["protocol"],
            addressRange=doc["addressRange"],
        )

    def parse_group(doc: dict) -> Group:
        return Group(
            name=doc["name"],
            typeId=doc["typeId"],
        )

    return Infrastructure(
        nodes={
            ndoc["name"]: parse_infrastructure_node(ndoc)
            for ndoc in doc["nodes"]
        },
        networks={
            ndoc["name"]: parse_network(ndoc) for ndoc in doc["networks"]
        },
        groups={
            gdoc["name"]: parse_group(gdoc) for gdoc in doc.get("groups", [])
        },
    )
