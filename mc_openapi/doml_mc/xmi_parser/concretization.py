from pyecore.ecore import EObject

from ..model.concretization import Concretization, Group, VirtualMachine, Provider, Storage, Network


def parse_concretization(doc: dict) -> Concretization:
    def parse_provider(doc: EObject) -> (Provider, list[VirtualMachine], list[Group], list[Storage], list[Network]):
        def parse_group(doc: EObject) -> Group:
            return Group(
                name=doc.name,
                maps=doc.maps.name,
            )

        def parse_virtual_machine(doc: EObject) -> VirtualMachine:
            return VirtualMachine(
                name=doc.name,
                maps=doc.maps.name,
            )

        def parse_storage(doc: EObject) -> Storage:
            return Storage(
                name=doc.name,
                maps=doc.maps,
            )

        def parse_network(doc: EObject) -> Network:
            return Network(
                name=doc.name,
                maps=doc.maps.name,
            )

        groups = list(map(parse_group, doc.group))
        vms = list(map(parse_virtual_machine, doc.vms))
        storages = list(map(parse_storage, doc.storages))
        networks = list(map(parse_network, doc.networks))
        provider = Provider(
            name=doc.name,
            supportedGroups=[g.name for g in groups],
            providedVMs=[vm.name for vm in vms],
            storages=[st.name for st in storages],
            providedNetworks=[net.name for net in networks],
            description=doc.description,
        )
        return (provider, vms, groups, storages, networks)

    groups, vms, providers, storages, networks = ({}, {}, {}, {}, {})
    for provdoc in doc.providers:
        prov, pvms, pgroups, pstorages, pnets = parse_provider(provdoc)
        providers[prov.name] = prov
        vms |= {vm.name: vm for vm in pvms}
        groups |= {gr.name: gr for gr in pgroups}
        storages |= {st.name: st for st in pstorages}
        networks |= {net.name: net for net in pnets}

    return Concretization(
        name=doc.name,
        groups=groups,
        vms=vms,
        providers=providers,
        storages=storages,
        networks=networks,
    )
