from collections.abc import Callable
from dataclasses import dataclass

from z3 import (
    Context, FuncDeclRef, Solver, ExprRef, SortRef, DatatypeSortRef, unsat
)

from .intermediate_model.doml_element import IntermediateModel
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
from .mc_result import MCResult, MCResults


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


@dataclass
class Requirement:
    assert_callable: Callable[[SMTEncoding, SMTSorts], list[ExprRef]]
    assert_name: str
    description: str
    error_description: str


class RequirementStore:
    def __init__(self, requirements: list[Requirement]):
        self.requirements = requirements
        pass

    def get_all_requirements(self) -> list[Requirement]:
        return self.requirements

    def get_num_requirements(self) -> int:
        return len(self.get_all_requirements())

    def get_one_requirement(self, index: int) -> Requirement:
        return self.get_all_requirements()[index]


class IntermediateModelChecker:
    def __init__(self, metamodel, inv_assoc, intermediate_model: IntermediateModel):
        def instantiate_solver():
            self.z3Context = Context()
            self.solver = Solver(ctx=self.z3Context)

            class_sort, class_ = mk_class_sort_dict(self.metamodel, self.z3Context)
            assoc_sort, assoc = mk_association_sort_dict(self.metamodel, self.z3Context)
            attr_sort, attr = mk_attribute_sort_dict(self.metamodel, self.z3Context)
            elem_sort, elem = mk_elem_sort_dict(self.intermediate_model, self.z3Context)
            ss_sort, ss = mk_stringsym_sort_dict(self.intermediate_model, self.metamodel, self.z3Context)
            AData = mk_adata_sort(ss_sort, self.z3Context)
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
                self.metamodel,
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

        self.metamodel = metamodel
        self.inv_assoc = inv_assoc
        self.intermediate_model = intermediate_model
        instantiate_solver()

    def check_consistency_constraints(self) -> tuple[MCResult, str]:
        self.solver.push()
        self.assert_consistency_constraints()
        res = self.solver.check()
        self.solver.pop()
        if res == unsat:
            return MCResult.unsat, "The DOML model is inconsistent."
        else:
            return MCResult.from_z3result(res), ""

    def check_requirements(self, reqs: RequirementStore) -> MCResults:
        results = []

        for req in reqs.get_all_requirements():
            self.solver.push()
            self.solver.assert_and_track(
                req.assert_callable(self.smt_encoding, self.smt_sorts),
                req.assert_name
                )
            res = self.solver.check()
            self.solver.pop()
            results.append((MCResult.from_z3result(res, flipped=True), req.error_description))

        return MCResults(results)

    def assert_consistency_constraints(self):
        assert_attribute_rel_constraints(
            self.metamodel,
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
            self.metamodel,
            self.solver,
            self.smt_encoding.association_rel,
            self.smt_encoding.associations,
            self.smt_encoding.classes,
            self.smt_encoding.element_class_fun,
            self.smt_sorts.element_sort,
            self.inv_assoc
        )
