# vm, iface = get_consts(smtsorts, ["vm", "iface"])
# return And(
#     smtenc.element_class_fun(vm) == smtenc.classes["infrastructure_VirtualMachine"],
#     Not(
#         Exists(
#             [iface],
#             ENCODINGS.association_rel(vm, smtenc.associations["infrastructure_ComputingNode::ifaces"], iface)
#         )
#     )
# )

>   "Something that will be unsatisfiable"
    vm is class infrastructure.VirtualMachine
    and
    not exists iface (
        vm has association infrastructure.ComputingNode->ifaces iface
        and
        vm has association infrastructure.ComputingNode->ifaces iface
        or
        vm has attribute infrastructure.ComputingNode->os Os1
        and
        vm has attribute infrastructure.ComputingNode->memory_mb 1024
        and
        vm has attribute infrastructure.ComputingNode->architecture "linux"
        and
        vm has attribute infrastructure.ComputingNode->architecture "linux"
        and
        vm has attribute infrastructure.Location->region "europe"
        and
        vm has attribute application.SoftwareComponent->isPersistent true
    )
    ---
    "VM {vm} has some problems."

>   "All VMs have at least one interface 2"
    vm is class infrastructure.VirtualMachine
    and
    not exists iface (
        vm has association infrastructure.ComputingNode->ifaces iface
    )
    ---
    "VM {vm} has no associated interface."

>   "All VMs have at least one interface 3"
    vm is class infrastructure.VirtualMachine
    and
    exists iface (
        vm has association infrastructure.ComputingNode->ifaces iface
    )
    ---
    "Virtual Machine {vm} has no associated interface."