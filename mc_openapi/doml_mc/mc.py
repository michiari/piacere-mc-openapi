import importlib.resources as ilres

import yaml
from dataclasses import dataclass

from z3 import (
    CheckSatResult, Consts, ExprRef, FuncDeclRef, Solver, SortRef, DatatypeSortRef,
    ForAll, Exists, Implies, And, Or,
    sat, unsat, unknown
)

from .. import assets
from .intermediate_model.doml_element import reciprocate_inverse_associations
from .intermediate_model.metamodel import (
    parse_inverse_associations,
    parse_metamodel
)
from .xmi_parser.doml_model import parse_doml_model
from .z3encoding.im_encoding import (
    assert_im_associations_q, assert_im_attributes,
    def_elem_class_f_and_assert_classes,
    mk_elem_sort_dict, mk_stringsym_sort_dict
)
from .z3encoding.metamodel_encoding import (
    def_association_rel,
    assert_association_rel_constraints,
    def_attribute_rel,
    assert_attribute_rel_constraints,
    mk_association_sort_dict,
    mk_attribute_sort_dict, mk_class_sort_dict
)
from .z3encoding.types import Refs
from .z3encoding.utils import mk_adata_sort


@dataclass
class SMTEncoding:
    classes: Refs
    associations: Refs
    attributes: Refs
    elements: Refs
    str_symbols: Refs
    element_class_fun: FuncDeclRef
    attribute_rel: FuncDeclRef
    association_rel: FuncDeclRef


@dataclass
class SMTSorts:
    class_sort: SortRef
    association_sort: SortRef
    attribute_sort: SortRef
    element_sort: SortRef
    str_symbols_sort: SortRef
    attr_data_sort: DatatypeSortRef


class ModelChecker:
    metamodel = None
    inv_assoc = None

    @staticmethod
    def init_metamodel():
        mmdoc = yaml.load(ilres.read_text(assets, "doml_meta.yaml"), yaml.Loader)
        ModelChecker.metamodel = parse_metamodel(mmdoc)
        ModelChecker.inv_assoc = parse_inverse_associations(mmdoc)

    def __init__(self, xmi_model: bytes):
        def instantiate_solver():
            self.solver = Solver()

            class_sort, class_ = mk_class_sort_dict(ModelChecker.metamodel)
            assoc_sort, assoc = mk_association_sort_dict(ModelChecker.metamodel)
            attr_sort, attr = mk_attribute_sort_dict(ModelChecker.metamodel)
            elem_sort, elem = mk_elem_sort_dict(self.intermediate_model)
            ss_sort, ss = mk_stringsym_sort_dict(self.intermediate_model, ModelChecker.metamodel)
            AData = mk_adata_sort(ss_sort)
            elem_class_f = def_elem_class_f_and_assert_classes(
                self.intermediate_model,
                self.solver,
                elem_sort,
                elem,
                class_sort,
                class_
            )
            attr_rel = def_attribute_rel(
                attr_sort,
                elem_sort,
                AData
            )
            assert_im_attributes(
                attr_rel,
                self.solver,
                self.intermediate_model,
                ModelChecker.metamodel,
                elem,
                attr_sort,
                attr,
                AData,
                ss
            )
            assoc_rel = def_association_rel(
                assoc_sort,
                elem_sort
            )
            assert_im_associations_q(
                assoc_rel,
                self.solver,
                {k: v for k, v in self.intermediate_model.items()},
                elem,
                assoc_sort,
                assoc,
            )
            self.smt_encoding = SMTEncoding(
                class_,
                assoc,
                attr,
                elem,
                ss,
                elem_class_f,
                attr_rel,
                assoc_rel
            )
            self.smt_sorts = SMTSorts(
                class_sort,
                assoc_sort,
                attr_sort,
                elem_sort,
                ss_sort,
                AData
            )

        assert ModelChecker.metamodel and ModelChecker.inv_assoc
        self.intermediate_model = parse_doml_model(xmi_model, ModelChecker.metamodel)
        reciprocate_inverse_associations(self.intermediate_model, ModelChecker.inv_assoc)
        instantiate_solver()

    def check_common_requirements(self) -> tuple[CheckSatResult, str]:
        some_dontknow = False

        self.solver.push()
        self.assert_consistency_constraints()
        res = self.solver.check()
        if res == unsat:
            return res, "The DOML model is inconsistent."
        elif res == unknown:
            some_dontknow = True
        self.solver.pop()

        common_requirements = self.get_common_requirements()
        for expr_thunk, assert_name, _, err_msg in common_requirements:
            self.solver.push()
            self.solver.assert_and_track(expr_thunk(), "vm_iface")
            res = self.solver.check()
            if res == unsat:
                return res, err_msg
            elif res == unknown:
                some_dontknow = True
            self.solver.pop()

        if some_dontknow:
            return unknown, "Unable to check some requirements."
        else:
            return sat, "All requirements satisfied."

    def get_consts(self, consts: list[str]) -> list[ExprRef]:
        return Consts(" ".join(consts), self.smt_sorts.element_sort)

    def assert_consistency_constraints(self):
        assert_attribute_rel_constraints(
            ModelChecker.metamodel,
            self.solver,
            self.smt_encoding.attribute_rel,
            self.smt_encoding.attributes,
            self.smt_encoding.classes,
            self.smt_encoding.element_class_fun,
            self.smt_sorts.element_sort,
            self.smt_sorts.attr_data_sort,
            self.smt_encoding.str_symbols
        )
        assert_association_rel_constraints(
            ModelChecker.metamodel,
            self.solver,
            self.smt_encoding.association_rel,
            self.smt_encoding.associations,
            self.smt_encoding.classes,
            self.smt_encoding.element_class_fun,
            self.smt_sorts.element_sort,
            ModelChecker.inv_assoc
        )

    def get_common_requirements(self):
        smtenc = self.smt_encoding

        def vm_iface():
            vm, iface = self.get_consts(["vm", "iface"])
            return ForAll(
                [vm],
                Implies(
                    smtenc.element_class_fun(vm) == smtenc.classes["infrastructure_VirtualMachine"],
                    Exists(
                        [iface],
                        And(
                            smtenc.association_rel(vm, smtenc.associations["infrastructure_ComputingNode::ifaces"], iface)
                        )
                    )
                )
            )

        def software_package_iface_net():
            asc_consumer, asc_exposer, siface, net, net_iface, cn, vm, deployment, dc = self.get_consts(
                ["asc_consumer", "asc_exposer", "siface", "net", "net_iface", "cn", "vm", "deployment", "dc"]
            )
            return ForAll(
                [asc_consumer, asc_exposer, siface],
                Implies(
                    And(
                        smtenc.association_rel(asc_consumer, smtenc.associations["application_SoftwareComponent::exposedInterfaces"], siface),
                        smtenc.association_rel(asc_exposer, smtenc.associations["application_SoftwareComponent::consumedInterfaces"], siface),
                    ),
                    Exists(
                        [net],
                        And(
                            Or(
                                Exists(
                                    [cn, deployment, net_iface],
                                    And(  # asc_consumer is deployed on a component with an interface in network n
                                        smtenc.association_rel(deployment, smtenc.associations["commons_Deployment::component"], asc_consumer),
                                        smtenc.association_rel(deployment, smtenc.associations["commons_Deployment::node"], cn),
                                        smtenc.association_rel(cn, smtenc.associations["infrastructure_ComputingNode::ifaces"], net_iface),
                                        smtenc.association_rel(net_iface, smtenc.associations["infrastructure_NetworkInterface::belongsTo"], net),
                                    ),
                                ),
                                Exists(  # asc_consumer is deployed on a container hosting a VM with an interface in network n
                                    [cn, deployment, vm, net_iface],
                                    And(
                                        smtenc.association_rel(deployment, smtenc.associations["commons_Deployment::component"], asc_consumer),
                                        smtenc.association_rel(deployment, smtenc.associations["commons_Deployment::node"], cn),
                                        smtenc.association_rel(cn, smtenc.associations["infrastructure_Container::hosts"], vm),
                                        smtenc.association_rel(vm, smtenc.associations["infrastructure_ComputingNode::ifaces"], net_iface),
                                        smtenc.association_rel(net_iface, smtenc.associations["infrastructure_NetworkInterface::belongsTo"], net),
                                    ),
                                ),
                            ),
                            Or(
                                Exists(
                                    [cn, deployment, net_iface],
                                    And(  # asc_exposer is deployed on a component with an interface in network n
                                        smtenc.association_rel(deployment, smtenc.associations["commons_Deployment::component"], asc_exposer),
                                        smtenc.association_rel(deployment, smtenc.associations["commons_Deployment::node"], cn),
                                        smtenc.association_rel(cn, smtenc.associations["infrastructure_ComputingNode::ifaces"], net_iface),
                                        smtenc.association_rel(net_iface, smtenc.associations["infrastructure_NetworkInterface::belongsTo"], net),
                                    ),
                                ),
                                Exists(  # asc_exposer is deployed on a container hosting a VM with an interface in network n
                                    [cn, deployment, vm, net_iface],
                                    And(
                                        smtenc.association_rel(deployment, smtenc.associations["commons_Deployment::component"], asc_exposer),
                                        smtenc.association_rel(deployment, smtenc.associations["commons_Deployment::node"], cn),
                                        smtenc.association_rel(cn, smtenc.associations["infrastructure_Container::hosts"], vm),
                                        smtenc.association_rel(vm, smtenc.associations["infrastructure_ComputingNode::ifaces"], net_iface),
                                        smtenc.association_rel(net_iface, smtenc.associations["infrastructure_NetworkInterface::belongsTo"], net),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            )

        def iface_uniq():
            def any_iface(elem, iface):
                ifaces_assocs = [
                    "infrastructure_ComputingNode::ifaces",
                    "infrastructure_Storage::ifaces",
                    "infrastructure_FunctionAsAService::ifaces"
                ]
                return Or(*(smtenc.association_rel(elem, smtenc.associations[assoc_name], iface) for assoc_name in ifaces_assocs))

            e1, e2, ni = self.get_consts(["e1", "e2", "i"])
            return ForAll(
                [e1, e2, ni],
                Implies(
                    And(any_iface(e1, ni), any_iface(e2, ni)),
                    e1 == e2
                )
            )

        def all_SoftwareComponents_deployed():
            sc, deployment, ielem = self.get_consts(["sc", "deployment", "ielem"])
            return ForAll(
                [sc],
                Implies(
                    smtenc.element_class_fun(sc) == smtenc.classes["application_SoftwareComponent"],
                    Exists(
                        [deployment, ielem],
                        And(
                            smtenc.association_rel(deployment, smtenc.associations["commons_Deployment::component"], sc),
                            smtenc.association_rel(deployment, smtenc.associations["commons_Deployment::node"], ielem)
                        )
                    )
                )
            )

        def all_infrastructure_elements_deployed():
            def checkOneClass(ielem, concr, provider, celem, ielemClass, providerAssoc, celemAssoc):
                return Implies(
                    smtenc.element_class_fun(ielem) == smtenc.classes[ielemClass],
                    Exists(
                        [provider, celem],
                        And(
                            smtenc.association_rel(concr, smtenc.associations["concrete_ConcreteInfrastructure::providers"], provider),
                            smtenc.association_rel(provider, smtenc.associations[providerAssoc], celem),
                            smtenc.association_rel(celem, smtenc.associations[celemAssoc], ielem)
                        )
                    )
                )

            ielem, concr, provider, celem = self.get_consts(["ielem", "concr", "provider", "celem"])
            return Exists(
                [concr],
                And(
                    smtenc.element_class_fun(concr) == smtenc.classes["concrete_ConcreteInfrastructure"],
                    ForAll(
                        [ielem],
                        And(
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
                )
            )

        return [
            (vm_iface, "vm_iface", "All virtual machines must be connected to at least one network interface.", "A virtual machine is connected to no network interface."),
            (software_package_iface_net, "software_package_iface_net", "All software packages can see the interfaces they need through a common network.", "A software package is deployed on a node that has no access to an interface it consumes."),
            (iface_uniq, "iface_uniq", "There are no duplicated interfaces.", "There is a duplicated interface."),
            (all_SoftwareComponents_deployed, "all_SoftwareComponents_deployed", "All software components have been deployed to some node.", "A software component has not been deployed to any node."),
            (all_infrastructure_elements_deployed, "all_infrastructure_elements_deployed", "All abstract infrastructure elements are mapped to an element in the active concretization.", "An abstract infrastructure element has not been mapped to any element in the active concretization."),
        ]
