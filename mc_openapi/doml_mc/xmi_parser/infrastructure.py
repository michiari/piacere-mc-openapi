from pyecore.ecore import EObject

from mc_openapi.doml_mc.intermediate_model.doml_element import parse_attrs_and_assocs_from_doc

from ..intermediate_model.metamodel import MetaModel
from ..model.infrastructure import Infrastructure, InfrastructureNode, Network, NetworkInterface, Group


def parse_infrastructure(doc: EObject, mm: MetaModel) -> Infrastructure:
    def parse_infrastructure_node(doc: EObject) -> InfrastructureNode:
        def parse_network_interface(doc: EObject) -> NetworkInterface:
            return NetworkInterface(
                name=doc.name,
                belongsTo=doc.belongsTo.name,
                endPoint=doc.endPoint,
            )

        if doc.eClass.name == "AutoScalingGroup":
            doc = doc.machineDefinition

        typeId = "infrastructure_" + doc.eClass.name
        annotations_dict = {a.key: a.value for a in doc.annotations}
        attrs, assocs = parse_attrs_and_assocs_from_doc(annotations_dict, typeId, mm)
        return InfrastructureNode(
            name=doc.name,
            typeId=typeId,
            network_interfaces={
                niface_doc.name: parse_network_interface(niface_doc)
                for niface_doc in doc.ifaces
            },
            attributes=attrs,
            associations=assocs,
        )

    def parse_network(doc: EObject) -> Network:
        return Network(
            name=doc.name,
            protocol=doc.protocol,
            addressRange=doc.addressRange,
        )

    def parse_group(doc: EObject) -> Group:
        return Group(
            name=doc.name,
            typeId="infrastructure_" + doc.eClass.name,
        )

    return Infrastructure(
        nodes={
            inode.name: inode
            for inode in map(parse_infrastructure_node, doc.nodes)
        },
        networks={
            ndoc.name: parse_network(ndoc) for ndoc in doc.networks
        },
        groups={
            gdoc.name: parse_group(gdoc) for gdoc in doc.secGroups
        },
    )
