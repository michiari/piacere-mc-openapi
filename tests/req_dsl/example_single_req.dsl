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

-   "All VMs have at least one interface 1"
    vm is class infrastructure.VirtualMachine
    and
    not exists iface (
        vm has association infrastructure.ComputingNode->ifaces iface
    )
    ---
    "VM {vm} has no associated interface."
