from typing import Union
from itertools import product

from z3 import (
    And,
    Const,
    DatatypeRef,
    DatatypeSortRef,
    ForAll,
    FuncDeclRef,
    Function,
    Or,
    Solver,
)

from ..intermediate_model import IntermediateModel, MetaModel
from ..intermediate_model.metamodel import get_mangled_attribute_defaults

from .types import Refs, SortAndRefs
from .utils import (
    assert_relation_tuples,
    Iff,
    mk_enum_sort_dict,
    mk_stringsym_sort_from_strings,
)


def mk_elem_sort_dict(
    im: IntermediateModel, additional_elems: list[str] = []
) -> SortAndRefs:
    return mk_enum_sort_dict("Element", list(im) + additional_elems)


def def_elem_class_f_and_assert_classes(
    im: IntermediateModel,
    solver: Solver,
    elem_sort: DatatypeSortRef,
    elem: Refs,
    class_sort: DatatypeSortRef,
    class_: Refs,
) -> FuncDeclRef:
    """
    ### Effects
    This procedure is effectful on `solver`.
    """
    elem_class_f = Function("elem_class", elem_sort, class_sort)
    for ename, e in im.items():
        solver.assert_and_track(
            elem_class_f(elem[ename]) == class_[e.class_],
            f"elem_class {ename} {e.class_}",
        )
    return elem_class_f


def assert_im_attributes(
    attr_rel: FuncDeclRef,
    solver: Solver,
    im: IntermediateModel,
    mm: MetaModel,
    elem: Refs,
    attr_sort: DatatypeSortRef,
    attr: Refs,
    AData: DatatypeSortRef,
    ss: Refs,
) -> None:
    """
    ### Effects
    This procedure is effectful on `solver`.
    """

    def encode_adata(v: Union[str, int, bool]) -> DatatypeRef:
        if type(v) is str:
            return AData.ss(ss[v])  # type: ignore
        elif type(v) is int:
            return AData.int(v)  # type: ignore
        else:  # type(v) is bool
            return AData.bool(v)  # type: ignore

    a = Const("a", attr_sort)
    d = Const("d", AData)
    for esn, im_es in im.items():
        mangled_attrs = (
            get_mangled_attribute_defaults(mm, im_es.class_) | im_es.attributes
        )
        assn = ForAll(
            [a, d],
            Iff(
                attr_rel(elem[esn], a, d),
                Or(
                    *(
                        And(
                            a == attr[amn],
                            d == encode_adata(avalue),
                        )
                        for amn, avalue in mangled_attrs.items()
                    )
                ),
            ),
        )
        solver.assert_and_track(assn, f"attribute_values {esn}")


def assert_im_associations(
    assoc_rel: FuncDeclRef,
    solver: Solver,
    im: IntermediateModel,
    mm: MetaModel,
    elem: Refs,
    assoc: Refs,
) -> None:
    """
    ### Effects
    This procedure is effectful on `solver`.
    """
    elem_names = set(im.keys())
    assoc_mangled_names = {
        f"{cname}::{aname}"
        for cname, c in mm.items()
        for aname in c.associations
    }
    rel_tpls = [
        [esn, amn, etn]
        for esn, amn, etn in product(
            elem_names, assoc_mangled_names, elem_names
        )
        if etn in im[esn].associations.get(amn, set())
    ]
    assert_relation_tuples(assoc_rel, solver, rel_tpls, elem, assoc, elem)


def assert_im_associations_q(
    assoc_rel: FuncDeclRef,
    solver: Solver,
    im: IntermediateModel,
    elem: Refs,
    assoc_sort: DatatypeSortRef,
    assoc: Refs,
) -> None:
    """
    ### Effects
    This procedure is effectful on `solver`.
    """

    a = Const("a", assoc_sort)
    for (esn, im_es), etn in product(im.items(), im):
        assn = ForAll(
            [a],
            Iff(
                assoc_rel(elem[esn], a, elem[etn]),
                Or(
                    *(
                        a == assoc[amn]
                        for amn, etns in im_es.associations.items()
                        if etn in etns
                    )
                ),
            ),
        )
        solver.assert_and_track(assn, f"associations {esn} {etn}")


def mk_stringsym_sort_dict(
    im: IntermediateModel,
    mm: MetaModel,
) -> SortAndRefs:
    strings = (
        {
            v
            for e in im.values()
            for v in e.attributes.values()
            if type(v) is str
        }
        | {
            a.default
            for c in mm.values()
            for a in c.attributes.values()
            if type(a.default) is str
        }
        | {"SCRIPT", "IMAGE"}  # GeneratorKind values
    )
    return mk_stringsym_sort_from_strings(list(strings))
