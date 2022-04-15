from .._utils import merge_dicts
from ..model.concretization import (
    Concretization,
    Group,
    Network,
    Provider,
    Storage,
    VirtualMachine,
)

from .doml_element import DOMLElement
from .types import IntermediateModel


def concretization_to_im(conc: Concretization) -> IntermediateModel:
    def group_to_im(g: Group) -> IntermediateModel:
        return {
            g.name: DOMLElement(
                name=g.name,
                class_="concrete_AutoScalingGroup",
                attributes={"commons_DOMLElement::name": g.name},
                associations={"concrete_AutoScalingGroup::maps": {g.maps}},
            )
        }

    def vm_to_im(vm: VirtualMachine) -> IntermediateModel:
        return {
            vm.name: DOMLElement(
                name=vm.name,
                class_="concrete_VirtualMachine",
                attributes={"commons_DOMLElement::name": vm.name},
                associations={"concrete_VirtualMachine::maps": {vm.maps}},
            )
        }

    def storage_to_im(s: Storage) -> IntermediateModel:
        return {
            s.name: DOMLElement(
                name=s.name,
                class_="concrete_Storage",
                attributes={"commons_DOMLElement::name": s.name},
                associations={"concrete_Storage::maps": {s.maps}},
            )
        }

    def network_to_im(n: Network) -> IntermediateModel:
        return {
            n.name: DOMLElement(
                name=n.name,
                class_="concrete_Network",
                attributes={"commons_DOMLElement::name": n.name},
                associations={"concrete_Network::maps": {n.maps}},
            )
        }

    def provider_to_im(p: Provider) -> IntermediateModel:
        return {
            p.name: DOMLElement(
                name=p.name,
                class_="concrete_RuntimeProvider",
                attributes={"commons_DOMLElement::name": p.name},
                associations={
                    "concrete_RuntimeProvider::supportedGroups": set(
                        p.supportedGroups
                    ),
                    "concrete_RuntimeProvider::vms": set(p.providedVMs),
                    "concrete_RuntimeProvider::networks": set(
                        p.providedNetworks
                    ),
                    "concrete_RuntimeProvider::storages": set(p.storages),
                },
            )
        }

    im_groups = merge_dicts(group_to_im(g) for g in conc.groups.values())
    im_vms = merge_dicts(vm_to_im(vm) for vm in conc.vms.values())
    im_providers = merge_dicts(
        provider_to_im(p) for p in conc.providers.values()
    )
    im_storages = merge_dicts(storage_to_im(s) for s in conc.storages.values())
    im_networks = merge_dicts(network_to_im(n) for n in conc.networks.values())

    return (
        {
            conc.name: DOMLElement(
                name=conc.name,
                class_="concrete_ConcreteInfrastructure",
                attributes={"commons_DOMLElement::name": conc.name},
                associations={
                    "concrete_ConcreteInfrastructure::providers": set(
                        im_providers
                    ),
                    "concrete_ConcreteInfrastructure::nodes": set(im_vms),
                    "concrete_ConcreteInfrastructure::asGroups": set(
                        im_groups
                    ),
                    "concrete_ConcreteInfrastructure::networks": set(
                        im_networks
                    ),
                    "concrete_ConcreteInfrastructure::storages": set(
                        im_storages
                    ),
                },
            )
        }
        | im_groups
        | im_vms
        | im_providers
        | im_storages
        | im_networks
    )
