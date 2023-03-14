from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from z3 import (Context, DatatypeSortRef, ExprRef, FuncDeclRef, Solver,
                SortRef, sat)

from mc_openapi.doml_mc.stats import STATS

from .intermediate_model.doml_element import IntermediateModel
from .mc_result import MCResult, MCResults
from .z3encoding.im_encoding import (assert_im_associations,
                                     assert_im_attributes,
                                     def_elem_class_f_and_assert_classes, mk_attr_data_sort,
                                     mk_elem_sort_dict, mk_stringsym_sort_dict)
from .z3encoding.metamodel_encoding import (def_association_rel,
                                            def_attribute_rel,
                                            mk_association_sort_dict,
                                            mk_attribute_sort_dict,
                                            mk_class_sort_dict)
from .z3encoding.types import Refs


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
    assert_callable: Callable[[SMTEncoding, SMTSorts], ExprRef]
    assert_name: str
    description: str
    error_description: tuple[Literal["BUILTIN", "USER"],
                             Callable[[Solver, SMTSorts, IntermediateModel], str]]
    flipped: bool = False


class RequirementStore:
    def __init__(self, requirements: list[Requirement] = []):
        self.requirements = requirements
        pass

    def get_all_requirements(self) -> list[Requirement]:
        return self.requirements

    def get_one_requirement(self, index: int) -> Requirement:
        return self.get_all_requirements()[index]

    def __len__(self):
        return len(self.get_all_requirements())

    def __add__(self, other: "RequirementStore") -> "RequirementStore":
        return RequirementStore(self.requirements + other.requirements)


class IntermediateModelChecker:
    def __init__(self, metamodel, inv_assoc, intermediate_model: IntermediateModel):
        self.metamodel = metamodel
        self.inv_assoc = inv_assoc
        self.intermediate_model = intermediate_model
        self.instantiate_solver()

    def instantiate_solver(self, user_string_values=[]):
        self.z3Context = Context()
        self.solver = Solver(ctx=self.z3Context)

        class_sort, class_ = mk_class_sort_dict(self.metamodel, self.z3Context)
        assoc_sort, assoc = mk_association_sort_dict(
            self.metamodel, self.z3Context)
        attr_sort, attr = mk_attribute_sort_dict(
            self.metamodel, self.z3Context)
        elem_sort, elem = mk_elem_sort_dict(
            self.intermediate_model, self.z3Context)
        str_sort, str = mk_stringsym_sort_dict(
            self.intermediate_model,
            self.metamodel,
            self.z3Context,
            user_string_values
        )
        attr_data_sort = mk_attr_data_sort(str_sort, self.z3Context)
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
            attr_data_sort
        )
        assert_im_attributes(
            attr_rel,
            self.solver,
            self.intermediate_model,
            self.metamodel,
            elem,
            attr_sort,
            attr,
            attr_data_sort,
            str
        )
        assoc_rel = def_association_rel(
            assoc_sort,
            elem_sort
        )
        assert_im_associations(
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
            str,
            elem_class_f,
            attr_rel,
            assoc_rel
        )
        self.smt_sorts = SMTSorts(
            class_sort,
            assoc_sort,
            attr_sort,
            elem_sort,
            str_sort,
            attr_data_sort
        )

    def check_requirements(self, reqs: RequirementStore, timeout: int = 0) -> MCResults:
        self.solver.set(timeout=(timeout * 1000))

        results = []
        for req in reqs.get_all_requirements():
            self.solver.push()
            self.solver.assert_and_track(
                req.assert_callable(self.smt_encoding, self.smt_sorts),
                req.assert_name
            )
            res = self.solver.check()
            req_src, req_fn = req.error_description
            results.append((
                MCResult.from_z3result(res, flipped=req.flipped),
                req_src,
                req_fn(self.solver, self.smt_sorts, self.intermediate_model)
                # if res == sat else "" # not needed since we're try/catching model() errors
                # in each requirement now
            ))
            self.solver.pop()

        stats = self.solver.statistics()
        STATS.add(stats)
        return MCResults(results)
