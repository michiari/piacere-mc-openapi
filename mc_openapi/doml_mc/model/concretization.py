from dataclasses import dataclass


@dataclass
class Concretization:
    name: str
    groups: dict[str, "Group"]
    vms: dict[str, "VirtualMachine"]
    providers: dict[str, "Provider"]
    storages: dict[str, "Storage"]
    networks: dict[str, "Network"]


@dataclass
class Group:
    name: str
    maps: str


@dataclass
class VirtualMachine:
    name: str
    maps: str


@dataclass
class Provider:
    name: str
    supportedGroups: list[str]
    providedVMs: list[str]
    storages: list[str]
    providedNetworks: list[str]
    description: str


@dataclass
class Storage:
    name: str
    maps: str


@dataclass
class Network:
    name: str
    maps: str


def parse_concretization(doc: dict) -> Concretization:
    def parse_group(doc: dict) -> Group:
        return Group(
            name=doc["name"],
            maps=doc["maps"],
        )

    def parse_virtual_machine(doc: dict) -> VirtualMachine:
        return VirtualMachine(
            name=doc["name"],
            maps=doc["maps"],
        )

    def parse_provider(doc: dict) -> Provider:
        return Provider(
            name=doc["name"],
            supportedGroups=doc.get("supportedGroups", []),
            providedVMs=doc["providedVMs"],
            storages=doc.get("storages", []),
            providedNetworks=doc["providedNetworks"],
            description=doc.get("description", ""),
        )

    def parse_storage(doc: dict) -> Storage:
        return Storage(
            name=doc["name"],
            maps=doc["maps"],
        )

    def parse_network(doc: dict) -> Network:
        return Network(
            name=doc["name"],
            maps=doc["maps"],
        )

    return Concretization(
        name=doc["name"],
        groups={
            gdoc["name"]: parse_group(gdoc) for gdoc in doc.get("asGroups", [])
        },
        vms={
            vmdooc["name"]: parse_virtual_machine(vmdooc)
            for vmdooc in doc["vms"]
        },
        providers={
            pdoc["name"]: parse_provider(pdoc) for pdoc in doc["providers"]
        },
        storages={
            sdoc["name"]: parse_storage(sdoc)
            for sdoc in doc.get("storages", [])
        },
        networks={
            ndoc["name"]: parse_network(ndoc) for ndoc in doc["networks"]
        },
    )
