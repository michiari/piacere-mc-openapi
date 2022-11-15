-   "VM must have iface"
    vm is class infrastructure.VirtualMachine
    and
    not exists iface (
        vm has infrastructure.ComputingNode->ifaces iface
    )
    ---
    "VM {vm} must have iface {iface}"

+   "VM must have iface"
    forall vm (
        vm is class infrastructure.VirtualMachine
        implies
        exists iface (
            vm has infrastructure.ComputingNode->ifaces iface
        )
    )
    ---
    "VM {vm} must have iface {iface}"

-   "Iface must be unique"
    ni1 has infrastructure.NetworkInterface->endPoint Value
    and
    ni1 is not ni2
    and
    ni2 has infrastructure.NetworkInterface->endPoint Value
    ---
    "Iface {ni1} and {ni2} must have different values"
