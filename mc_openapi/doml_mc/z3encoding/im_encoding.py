from itertools import product
from typing import Union

from z3 import (And, BoolSort, Const, Context, Datatype, DatatypeRef,
                DatatypeSortRef, ForAll, FuncDeclRef, Function, IntSort, Not,
                Or, Solver, EnumSort)

from mc_openapi.doml_mc.z3encoding.metamodel_encoding import mk_enum_sort_dict

from ..intermediate_model import IntermediateModel, MetaModel
from ..intermediate_model.metamodel import get_mangled_attribute_defaults
from .types import Refs, SortAndRefs
from ..utils import Iff

def mk_elem_sort_dict(
    im: IntermediateModel,
    z3ctx: Context,
    additional_elems: list[str] = []
) -> SortAndRefs:
    return mk_enum_sort_dict("Element", list(im) + additional_elems, z3ctx=z3ctx)


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
    elems: Refs,
    attr_sort: DatatypeSortRef, # Relationship sort
    attrs: Refs, # Relationship data
    attr_data_sort: DatatypeSortRef, # Value sort
    strings: Refs,
    allow_placeholders: bool = False
) -> None:
    """
    ### Effects
    This procedure is effectful on `solver`.
    """

    def encode_attr_data(v: Union[str, int, bool]) -> DatatypeRef:
        if type(v) is str:
            return attr_data_sort.str(strings[v])  # type: ignore
        elif type(v) is int:
            return attr_data_sort.int(v)  # type: ignore
        else:  # type(v) is bool
            return attr_data_sort.bool(v)  # type: ignore

    a = Const("a", attr_sort)
    d = Const("d", attr_data_sort)
    for esn, im_es in im.items():
        attr_data = get_mangled_attribute_defaults(mm, im_es.class_) | im_es.attributes
        if attr_data:
            assn = ForAll(
                [a, d],
                Iff(
                    attr_rel(elems[esn], a, d),
                    Or(
                        *(
                            And(
                                a == attrs[aname],
                                d == encode_attr_data(avalue)
                            )
                            for aname, avalues in attr_data.items()
                            for avalue in avalues
                        )
                    ),
                ),
            )
        else:
            assn = ForAll(
                [a, d],
                Not(attr_rel(elems[esn], a, d))
            )
        solver.assert_and_track(assn, f"attribute_values {esn}")

def assert_im_associations(
    assoc_rel: FuncDeclRef,
    solver: Solver,
    im: IntermediateModel, # Contains only bounded elements
    elem: Refs,
    assoc_sort: DatatypeSortRef,
    assoc: Refs,
) -> None:
    """
    ### Effects
    This procedure is effectful on `solver`.
    """

    assoc_ref = Const("a", assoc_sort)
    for (elem_1_k, elem_1_v), elem_2_k in product(im.items(), im):
        assn = ForAll(
            [assoc_ref],
            Iff(
                assoc_rel(elem[elem_1_k], assoc_ref, elem[elem_2_k]),
                Or(
                    *(
                        assoc_ref == assoc[elem_1_assoc_k]
                        for elem_1_assoc_k, elem_1_assoc_elems_k in elem_1_v.associations.items()
                        if elem_2_k in elem_1_assoc_elems_k
                    ),
                    solver.ctx
                ),
            ),
        )
        solver.assert_and_track(assn, f"associations {elem_1_k} {elem_2_k}")


def mk_stringsym_sort_dict(
    im: IntermediateModel,
    mm: MetaModel,
    z3ctx: Context,
    additional_strings: list[str] = []
) -> SortAndRefs:
    strings = (
        {
            v
            for e in im.values()
            for vs in e.attributes.values()
            for v in vs
            if isinstance(v, str)
        }
        | {
            v
            for c in mm.values()
            for a in c.attributes.values()
            if a.default is not None
            for v in a.default
            if isinstance(v, str)
        }
        | {"SCRIPT", "IMAGE"}  # GeneratorKind values
        | {"INGRESS", "EGRESS"} # TODO: Check if this fix is required
        # It solves a KeyError when MC is run on openstack_template.domlx
        | {
            v
            for v in additional_strings
        }
    )
    return mk_stringsym_sort_from_strings(list(strings), z3ctx=z3ctx)

def mk_attr_data_sort(
    str_sort: DatatypeSortRef,
    z3ctx: Context
) -> DatatypeSortRef:
    attr_data = Datatype("AttributeData", ctx=z3ctx)
    attr_data.declare("placeholder")
    attr_data.declare("int", ("get_int", IntSort(ctx=z3ctx)))
    attr_data.declare("bool", ("get_bool", BoolSort(ctx=z3ctx)))
    attr_data.declare("str", ("get_str", str_sort)) # str_sort is the one returned by the function above
    return attr_data.create()

def mk_stringsym_sort_from_strings(
    strings: list[str],
    z3ctx: Context
) -> SortAndRefs:
    str_list = [f"str_{i}_{symbolize(s)}" for i, s in enumerate(strings)]
    string_sort, str_refs_dict = mk_enum_sort_dict("string", str_list, z3ctx=z3ctx)
    string_sort_dict = {
        s: str_refs_dict[str] for s, str in zip(strings, str_list)
    }
    return string_sort, string_sort_dict

def symbolize(s: str) -> str:
    return "".join([c.lower() if c.isalnum() else "_" for c in s[:16]])
