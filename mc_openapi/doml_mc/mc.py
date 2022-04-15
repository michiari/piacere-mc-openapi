import importlib.resources as ilres

import yaml
from dataclasses import dataclass

from z3 import (
    CheckSatResult, Consts, ExprRef, FuncDeclRef, Solver, SortRef,
    ForAll, Exists, Implies, And
)

from .. import assets
from .intermediate_model.doml_element import reciprocate_inverse_associations
from .intermediate_model.doml_model2im import doml_model_to_im
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
    def_association_rel_and_assert_constraints,
    def_attribute_rel_and_assert_constraints,
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
            unbound_elems = []  # TODO: add this later
            self.solver = Solver()

            class_sort, class_ = mk_class_sort_dict(ModelChecker.metamodel)
            assoc_sort, assoc = mk_association_sort_dict(ModelChecker.metamodel)
            attr_sort, attr = mk_attribute_sort_dict(ModelChecker.metamodel)
            elem_sort, elem = mk_elem_sort_dict(self.intermediate_model, unbound_elems)
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
            attr_rel = def_attribute_rel_and_assert_constraints(
                ModelChecker.metamodel,
                self.solver,
                attr_sort,
                attr,
                class_,
                elem_class_f,
                elem_sort,
                AData,
                ss
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
            assoc_rel = def_association_rel_and_assert_constraints(
                ModelChecker.metamodel,
                self.solver,
                assoc_sort,
                assoc,
                class_,
                elem_class_f,
                elem_sort,
                ModelChecker.inv_assoc
            )
            assert_im_associations_q(
                assoc_rel,
                self.solver,
                {k: v for k, v in self.intermediate_model.items() if k not in unbound_elems},
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
                ss_sort
            )

        assert ModelChecker.metamodel and ModelChecker.inv_assoc
        doml_model = parse_doml_model(xmi_model, ModelChecker.metamodel)
        self.intermediate_model = doml_model_to_im(doml_model, ModelChecker.metamodel)
        reciprocate_inverse_associations(self.intermediate_model, ModelChecker.inv_assoc)
        instantiate_solver()

    def get_consts(self, consts: list[str]) -> list[ExprRef]:
        return Consts(" ".join(consts), self.smt_sorts.element_sort)

    def check(self) -> CheckSatResult:
        return self.solver.check()

    def add_requirement(self, assertion: ExprRef, description: str):
        self.solver.assert_and_track(assertion, description)

    def add_common_requirements(self):
        vm, iface = self.get_consts(["vm", "iface"])
        smtenc = self.smt_encoding
        vmIfaceAssertion = ForAll(
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
        self.add_requirement(vmIfaceAssertion, "vm_iface")
