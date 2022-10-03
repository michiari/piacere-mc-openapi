from typing import Optional

from z3 import (
    Const, Consts, ExprRef,
    Exists, And, Or, Not,
    Solver, ModelRef
)

from .imc import (
    SMTEncoding, SMTSorts, Requirement, RequirementStore
)
from .intermediate_model.doml_element import IntermediateModel


def get_consts(smtsorts: SMTSorts, consts: list[str]) -> list[ExprRef]:
    return Consts(" ".join(consts), smtsorts.element_sort)


# Assertions

def vm_iface(smtenc: SMTEncoding, smtsorts: SMTSorts) -> ExprRef:
    vm, iface = get_consts(smtsorts, ["vm", "iface"])
    return And(
        smtenc.element_class_fun(vm) == smtenc.classes["infrastructure_VirtualMachine"],
        Not(
            Exists(
                [iface],
                smtenc.association_rel(vm, smtenc.associations["infrastructure_ComputingNode::ifaces"], iface)
            )
        )
    )


def software_package_iface_net(smtenc: SMTEncoding, smtsorts: SMTSorts) -> ExprRef:
    asc_consumer, asc_exposer, siface, net, net_iface, cnode, cdeployment, enode, edeployment, vm, dc = get_consts(
        smtsorts,
        ["asc_consumer", "asc_exposer", "siface", "net", "net_iface", "cnode", "cdeployment", "enode", "edeployment", "vm", "dc"]
    )
    return And(
        smtenc.association_rel(asc_consumer, smtenc.associations["application_SoftwareComponent::exposedInterfaces"], siface),
        smtenc.association_rel(asc_exposer, smtenc.associations["application_SoftwareComponent::consumedInterfaces"], siface),
        Not(
            Exists(
                [cdeployment, cnode, edeployment, enode, net],
                And(
                    smtenc.association_rel(cdeployment, smtenc.associations["commons_Deployment::component"], asc_consumer),
                    smtenc.association_rel(cdeployment, smtenc.associations["commons_Deployment::node"], cnode),
                    Exists(
                        [vm, net_iface],
                        Or(
                            And(  # asc_consumer is deployed on a component with an interface in network n
                                smtenc.association_rel(cnode, smtenc.associations["infrastructure_ComputingNode::ifaces"], net_iface),
                                smtenc.association_rel(net_iface, smtenc.associations["infrastructure_NetworkInterface::belongsTo"], net),
                            ),
                            And(  # asc_consumer is deployed on a container hosted in a VM with an interface in network n
                                smtenc.association_rel(cnode, smtenc.associations["infrastructure_Container::hosts"], vm),
                                smtenc.association_rel(vm, smtenc.associations["infrastructure_ComputingNode::ifaces"], net_iface),
                                smtenc.association_rel(net_iface, smtenc.associations["infrastructure_NetworkInterface::belongsTo"], net),
                            ),
                            And(  # asc_consumer is deployed on a VM in an AutoScalingGroup with an interface in network n
                                smtenc.association_rel(cnode, smtenc.associations["infrastructure_AutoScalingGroup::machineDefinition"], vm),
                                smtenc.association_rel(vm, smtenc.associations["infrastructure_ComputingNode::ifaces"], net_iface),
                                smtenc.association_rel(net_iface, smtenc.associations["infrastructure_NetworkInterface::belongsTo"], net),
                            ),
                        )
                    ),
                    smtenc.association_rel(edeployment, smtenc.associations["commons_Deployment::component"], asc_exposer),
                    smtenc.association_rel(edeployment, smtenc.associations["commons_Deployment::node"], enode),
                    Exists(
                        [vm, net_iface],
                        Or(
                            And(  # asc_exposer is deployed on a component with an interface in network n
                                smtenc.association_rel(enode, smtenc.associations["infrastructure_ComputingNode::ifaces"], net_iface),
                                smtenc.association_rel(net_iface, smtenc.associations["infrastructure_NetworkInterface::belongsTo"], net),
                            ),
                            And(  # asc_exposer is deployed on a container hosted on a VM with an interface in network n
                                smtenc.association_rel(enode, smtenc.associations["infrastructure_Container::hosts"], vm),
                                smtenc.association_rel(vm, smtenc.associations["infrastructure_ComputingNode::ifaces"], net_iface),
                                smtenc.association_rel(net_iface, smtenc.associations["infrastructure_NetworkInterface::belongsTo"], net),
                            ),
                            And(  # asc_exposer is deployed on a VM in an AutoScalingGroup with an interface in network n
                                smtenc.association_rel(enode, smtenc.associations["infrastructure_AutoScalingGroup::machineDefinition"], vm),
                                smtenc.association_rel(vm, smtenc.associations["infrastructure_ComputingNode::ifaces"], net_iface),
                                smtenc.association_rel(net_iface, smtenc.associations["infrastructure_NetworkInterface::belongsTo"], net),
                            ),
                        )
                    )
                )
            )
        )
    )


def iface_uniq(smtenc: SMTEncoding, smtsorts: SMTSorts) -> ExprRef:
    endPointAttr = smtenc.attributes["infrastructure_NetworkInterface::endPoint"]
    ni1, ni2 = get_consts(smtsorts, ["ni1", "ni2"])
    value = Const("value", smtsorts.attr_data_sort)
    return And(
        smtenc.attribute_rel(ni1, endPointAttr, value),
        smtenc.attribute_rel(ni2, endPointAttr, value),
        ni1 != ni2,
    )


def all_SoftwareComponents_deployed(smtenc: SMTEncoding, smtsorts: SMTSorts) -> ExprRef:
    sc, deployment, ielem = get_consts(smtsorts, ["sc", "deployment", "ielem"])
    return And(
        smtenc.element_class_fun(sc) == smtenc.classes["application_SoftwareComponent"],
        Not(
            Exists(
                [deployment, ielem],
                And(
                    smtenc.association_rel(deployment, smtenc.associations["commons_Deployment::component"], sc),
                    smtenc.association_rel(deployment, smtenc.associations["commons_Deployment::node"], ielem),
                )
            )
        )
    )


def all_infrastructure_elements_deployed(smtenc: SMTEncoding, smtsorts: SMTSorts) -> ExprRef:
    def checkOneClass(ielem, concr, provider, celem, ielemClass, providerAssoc, celemAssoc):
        return And(
            smtenc.element_class_fun(ielem) == smtenc.classes[ielemClass],
            Not(
                Exists(
                    [provider, celem],
                    And(
                        smtenc.association_rel(concr, smtenc.associations["concrete_ConcreteInfrastructure::providers"], provider),
                        smtenc.association_rel(provider, smtenc.associations[providerAssoc], celem),
                        smtenc.association_rel(celem, smtenc.associations[celemAssoc], ielem)
                    )
                )
            )
        )

    ielem, concr, provider, celem = get_consts(smtsorts, ["ielem", "concr", "provider", "celem"])
    return And(
        smtenc.element_class_fun(concr) == smtenc.classes["concrete_ConcreteInfrastructure"],
        Or(
            checkOneClass(
                ielem, concr, provider, celem,
                "infrastructure_VirtualMachine",
                "concrete_RuntimeProvider::vms",
                "concrete_VirtualMachine::maps"
            ),
            checkOneClass(
                ielem, concr, provider, celem,
                "infrastructure_Network",
                "concrete_RuntimeProvider::networks",
                "concrete_Network::maps"
            ),
            checkOneClass(
                ielem, concr, provider, celem,
                "infrastructure_Storage",
                "concrete_RuntimeProvider::storages",
                "concrete_Storage::maps"
            ),
            checkOneClass(
                ielem, concr, provider, celem,
                "infrastructure_FunctionAsAService",
                "concrete_RuntimeProvider::faas",
                "concrete_FunctionAsAService::maps"
            ),
        )
    )


def all_concrete_map_something(smtenc: SMTEncoding, smtsorts: SMTSorts) -> ExprRef:
    def checkOneClass(ielem, provider, celem, providerAssoc, celemAssoc):
        return And(
            smtenc.association_rel(provider, smtenc.associations[providerAssoc], celem),
            Not(
                Exists(
                    [ielem],
                    smtenc.association_rel(celem, smtenc.associations[celemAssoc], ielem)
                )
            )
        )

    ielem, concr, provider, celem = get_consts(smtsorts, ["ielem", "concr", "provider", "celem"])
    return And(
        smtenc.element_class_fun(concr) == smtenc.classes["concrete_ConcreteInfrastructure"],
        smtenc.association_rel(concr, smtenc.associations["concrete_ConcreteInfrastructure::providers"], provider),
        Or(
            checkOneClass(
                ielem, provider, celem,
                "concrete_RuntimeProvider::vms",
                "concrete_VirtualMachine::maps"
            ),
            checkOneClass(
                ielem, provider, celem,
                "concrete_RuntimeProvider::vmImages",
                "concrete_VMImage::maps"
            ),
            checkOneClass(
                ielem, provider, celem,
                "concrete_RuntimeProvider::containerImages",
                "concrete_ContainerImage::maps"
            ),
            checkOneClass(
                ielem, provider, celem,
                "concrete_RuntimeProvider::networks",
                "concrete_Network::maps"
            ),
            checkOneClass(
                ielem, provider, celem,
                "concrete_RuntimeProvider::storages",
                "concrete_Storage::maps"
            ),
            checkOneClass(
                ielem, provider, celem,
                "concrete_RuntimeProvider::faas",
                "concrete_FunctionAsAService::maps"
            ),
            checkOneClass(
                ielem, provider, celem,
                "concrete_RuntimeProvider::group",
                "concrete_ComputingGroup::maps"
            ),
        )
    )


# Error Descriptions

def get_user_friendly_name(
    intermediate_model: IntermediateModel,
    model: ModelRef,
    const: ExprRef
) -> Optional[str]:
    z3_elem = model[const]
    if z3_elem is not None:
        im_elem = intermediate_model.get(str(z3_elem))
        if im_elem is not None:
            return im_elem.user_friendly_name
    return None


def ed_vm_iface(solver: Solver, smtsorts: SMTSorts, intermediate_model: IntermediateModel) -> str:
    vm = Const("vm", smtsorts.element_sort)
    vm_name = get_user_friendly_name(intermediate_model, solver.model(), vm)
    if vm_name:
        return f"Virtual machine {vm_name} is connected to no network interface."
    else:
        return "A virtual machine is connected to no network interface."


def ed_software_package_iface_net(solver: Solver, smtsorts: SMTSorts, intermediate_model: IntermediateModel) -> str:
    asc_consumer, asc_exposer, siface = get_consts(
        smtsorts,
        ["asc_consumer", "asc_exposer", "siface"]
    )
    model = solver.model()
    asc_consumer_name = get_user_friendly_name(intermediate_model, model, asc_consumer)
    asc_exposer_name = get_user_friendly_name(intermediate_model, model, asc_exposer)
    siface_name = get_user_friendly_name(intermediate_model, model, siface)
    if asc_consumer_name and asc_exposer_name and siface_name:
        return (
            f"Software components '{asc_consumer_name}' and '{asc_exposer_name}' "
            f"are supposed to communicate through interface '{siface_name}', "
            "but they are deployed to nodes that cannot communicate through a common network."
        )
    else:
        return "A software package is deployed on a node that has no access to an interface it consumes."


def ed_iface_uniq(solver: Solver, smtsorts: SMTSorts, intermediate_model: IntermediateModel) -> str:
    ni1, ni2 = get_consts(smtsorts, ["ni1", "ni2"])
    model = solver.model()
    ni1_name = get_user_friendly_name(intermediate_model, model, ni1)
    ni2_name = get_user_friendly_name(intermediate_model, model, ni2)
    if ni1_name and ni2_name:
        return f"Network interfaces '{ni1_name}' and '{ni2_name}' share the same IP address."
    else:
        return "Two network interfaces share the same IP address."


def ed_all_SoftwareComponents_deployed(solver: Solver, smtsorts: SMTSorts, intermediate_model: IntermediateModel) -> str:
    sc = Const("sc", smtsorts.element_sort)
    sc_name = get_user_friendly_name(intermediate_model, solver.model(), sc)
    if sc_name:
        return f"Software component '{sc_name}' is not deployed to any abstract infrastructure node."
    else:
        return "A software component has not been deployed to any node."


def ed_all_infrastructure_elements_deployed(solver: Solver, smtsorts: SMTSorts, intermediate_model: IntermediateModel) -> str:
    ielem = Const("ielem", smtsorts.element_sort)
    ielem_name = get_user_friendly_name(intermediate_model, solver.model(), ielem)
    if ielem_name:
        return f"Abstract infrastructure element '{ielem_name}' has not been mapped to any element in the active concretization."
    else:
        return "An abstract infrastructure element has not been mapped to any element in the active concretization."


def ed_all_concrete_map_something(solver: Solver, smtsorts: SMTSorts, intermediate_model: IntermediateModel) -> str:
    celem = Const("celem", smtsorts.element_sort)
    celem_name = get_user_friendly_name(intermediate_model, solver.model(), celem)
    if celem_name:
        return f"Concrete infrastructure element '{celem_name}' is mapped to no abstract infrastructure element."
    else:
        return "A concrete infrastructure element is mapped to no abstract infrastructure element."


CommonRequirements = RequirementStore(
    [
        Requirement(*rt) for rt in [
            (vm_iface, "vm_iface", "All virtual machines must be connected to at least one network interface.", ed_vm_iface),
            (software_package_iface_net, "software_package_iface_net", "All software packages can see the interfaces they need through a common network.", ed_software_package_iface_net),
            (iface_uniq, "iface_uniq", "There are no duplicated interfaces.", ed_iface_uniq),
            (all_SoftwareComponents_deployed, "all_SoftwareComponents_deployed", "All software components have been deployed to some node.", ed_all_SoftwareComponents_deployed),
            (all_infrastructure_elements_deployed, "all_infrastructure_elements_deployed", "All abstract infrastructure elements are mapped to an element in the active concretization.", ed_all_infrastructure_elements_deployed),
            (all_concrete_map_something, "all_concrete_map_something", "All elements in the active concretization are mapped to some abstract infrastructure element.", ed_all_concrete_map_something)
        ]
    ]
)
