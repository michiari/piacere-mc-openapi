

from dataclasses import dataclass
from itertools import product
from typing import Tuple

from z3 import (DatatypeRef, DatatypeSortRef, Not, FuncDeclRef, Model, Solver, sat,
                unsat)
from mc_openapi.doml_mc.imc import Requirement, SMTEncoding, SMTSorts
from mc_openapi.doml_mc.intermediate_model.doml_element import IntermediateModel

from mc_openapi.doml_mc.intermediate_model.metamodel import (DOMLVersion, MetaModel,
                                                             parse_metamodel)
from mc_openapi.doml_mc.xmi_parser.doml_model import parse_doml_model
from mc_openapi.doml_mc.z3encoding.im_encoding import (
    assert_im_associations, assert_im_attributes,
    def_elem_class_f_and_assert_classes, mk_attr_data_sort, mk_elem_sort_dict,
    mk_stringsym_sort_dict)
from mc_openapi.doml_mc.z3encoding.metamodel_encoding import (
    def_association_rel, def_attribute_rel, mk_association_sort_dict,
    mk_attribute_sort_dict, mk_class_sort_dict)
from mc_openapi.doml_mc.z3encoding.types import Refs

# Types
Elem = Value = Tuple[str, DatatypeRef]
AssocAndElems = Tuple[Elem, DatatypeRef, Elem]
AttrAndValues = Tuple[Elem, DatatypeRef, Value]

@dataclass
class Context:
    solver: Solver
    class_sort: DatatypeSortRef
    class_refs: Refs
    assoc_sort: DatatypeSortRef
    assoc_refs: Refs
    attr_sort: DatatypeSortRef
    attr_refs: Refs
    str_sort: DatatypeSortRef
    str_refs: Refs
    elem_sort: DatatypeSortRef
    elem_refs: Refs
    
    attr_data_sort: DatatypeSortRef

    elem_class_fn: FuncDeclRef
    attr_rel: FuncDeclRef
    assoc_rel: FuncDeclRef

    unbound_elems: list[str]
    unbound_values: Refs

class Synthesis:
    def __init__(self,
        metamodel: MetaModel,
        intermediate_model: IntermediateModel, 
    ) -> None:
        """
        Initialize the data required to synthetize a new DOML according to provided requirements.

        :param metamodel_input_file: The result of parsing the YAML metamodel file
        :param domlx_input_file: A XMI DOML file read as bytes containing the model to run through the tests.
        :param doml_version: The DOML version as an Enum.
        """
        self.mm = metamodel
        self.im = intermediate_model

    def _init_context(
        self,
        ub_elem_n : int = 0,
        ub_vals_n : int = 0,
        reqs : list[Requirement] = [],
        user_req_strings : list[str] = []
    ) -> Context:
        """Builds a Context object containing all the relationships sorts and refs.
        """
        solver = Solver()
        
        class_sort, class_refs = mk_class_sort_dict(self.mm, solver.ctx)
        assoc_sort, assoc_refs = mk_association_sort_dict(self.mm, solver.ctx)
        attr_sort, attr_refs = mk_attribute_sort_dict(self.mm, solver.ctx)
        str_sort, str_refs = mk_stringsym_sort_dict(self.im, self.mm, solver.ctx, user_req_strings)
        attr_data_sort = mk_attr_data_sort(str_sort, solver.ctx)

        unbound_elems = [f"unbound_elem_{i}" for i in range(ub_elem_n)]

        # Takes a list of strings and creates an Enum out of 'em
        elem_sort, elem_refs = mk_elem_sort_dict(self.im, solver.ctx, unbound_elems)

        unbound_values_names = [f"unbound_val_{i}" for i in range(ub_vals_n)]
        unbound_values = {
            name : attr_data_sort.placeholder for name in unbound_values_names
        }
        # Examples of values that can go in unbound_values:
        # ctx["attr_data_sort"].int(42), # ok
        # ctx["attr_data_sort"].bool(True), # ok
        # ctx["attr_data_sort"].str("x"), # cant do: it accept a ctx["str"][<str_key>] as input
        # Const("x", ctx["attr_data_sort"]) # cant do: it is a symbolic value that cannot be converted to a BoolRef expression

        elem_class_fn = def_elem_class_f_and_assert_classes(
            self.im,
            solver,
            elem_sort,
            elem_refs,
            class_sort,
            class_refs
        )
        
        # attr_rel :: (elem_sort, attr_sort, attr_data_sort) -> BoolRef
        attr_rel = def_attribute_rel(
            attr_sort,
            elem_sort,
            attr_data_sort
        )

        assert_im_attributes(
            attr_rel,
            solver,
            self.im,
            self.mm,
            elem_refs,
            attr_sort,
            attr_refs,
            attr_data_sort,
            str_refs
        )

        # assoc_rel :: (elem_sort, assoc_sort, elem_sort) -> BoolRef
        assoc_rel = def_association_rel(
            assoc_sort,
            elem_sort
        )
        
        assert_im_associations(
            assoc_rel,
            solver,
            {k: v for k, v in self.im.items() if k not in unbound_elems},
            elem_refs,
            assoc_sort,
            assoc_refs,
        )

        context = Context(
            solver,
            class_sort, class_refs,
            assoc_sort, assoc_refs,
            attr_sort, attr_refs,
            str_sort, str_refs,
            elem_sort, elem_refs,
            attr_data_sort,
            elem_class_fn,
            attr_rel,
            assoc_rel,
            unbound_elems,
            unbound_values
        )

        
        encodings = SMTEncoding(
            class_refs,
            assoc_refs,
            attr_refs,
            elem_refs,
            str_refs,
            elem_class_fn,
            attr_rel,
            assoc_rel
        )
        sorts = SMTSorts(
            class_sort,
            assoc_sort,
            attr_sort,
            elem_sort,
            str_sort,
            attr_data_sort
        )

        # Add requirements
        # TODO: Investigate whether it's possible or a good idea
        #       to handle each requirement individually, like in imc.py
        for req in reqs:
            req_fn = req.assert_callable(encodings, sorts)
            req_name = req.assert_name
            solver.assert_and_track(req_fn, req_name)

        return context

    def check(self,
        ub_elems_n: int = 0, 
        ub_vals_n: int = 0, 
        reqs: list = [], 
        curr_try: int = 0, 
        max_tries: int = 10,
        user_req_strings: list[str] = []
    ) -> Context:
        if curr_try > max_tries:
            raise RuntimeError("Max tries exceeded.")

        ctx = self._init_context(ub_elems_n, ub_vals_n, reqs, user_req_strings)

        res = ctx.solver.check()

        if res == sat:
            print(f"<Sat>\tub_elems_n={ub_elems_n}, ubvals_n={ub_vals_n}")
            return ctx
        elif res == unsat:
            print(f"<Unsat>\tub_elems_n={ub_elems_n}, ubvals_n={ub_vals_n}")
            if ub_elems_n > ub_vals_n:
                new_ub_vals_n = ub_vals_n * 2 if ub_vals_n >= 1 else 1
                return self.check(ub_elems_n, new_ub_vals_n, reqs, curr_try + 1, max_tries)
                # TODO: Choose which goes first in a smart way?
            elif ub_elems_n <= ub_vals_n:
                new_ub_elems_n = ub_elems_n * 2 if ub_elems_n >= 1 else 1
                return self.check(new_ub_elems_n, ub_vals_n, reqs, curr_try + 1, max_tries)
        else: # res == dontknow
            raise RuntimeError("It took too long to decide satifiability.")

    def get_ub_elems_and_assoc(self, ctx: Context, model: Model) -> list[AssocAndElems]:
        """Returns the associations between unbound elements."""
        return [ ((elem_1_k, elem_1_v), a, (elem_2_k, elem_2_v)) 
            for (elem_1_k, elem_1_v), a, (elem_2_k, elem_2_v) in product(ctx.elem_refs.items(), ctx.assoc_refs.values(), ctx.elem_refs.items()) 
            if (elem_1_k in ctx.unbound_elems or elem_2_k in ctx.unbound_elems) and model.eval(ctx.assoc_rel(elem_1_v, a, elem_2_v))
        ]

    def get_ub_vals_and_attr(self, ctx: Context, model: Model) -> list[AttrAndValues]:
        """Returns the attribute relationships between elements and attribute data/values."""
        return [ ((elem_k, elem_v), a, (ubval_k, ubval_v))
            for (elem_k, elem_v), a, (ubval_k, ubval_v) in product(ctx.elem_refs.items(), ctx.attr_refs.values(), ctx.unbound_values.items())
            if model.eval(ctx.attr_rel(elem_v, a, ubval_v))
        ]

    def pretty_ub_elems_assoc(self, assoc_elems: list[AssocAndElems]) -> str:
        """Returns a string containg a human-readable name of the elements and their association.
        """
        (elem_1_k, _), a, (elem_2_k, _) = assoc_elems
        elem_1 = self.im.get(elem_1_k)
        if elem_1:
            elem_1_name = f"{elem_1.class_} ({elem_1.user_friendly_name})" if elem_1_k[0:4] == "elem" else f"<'{elem_1_k}' not found>"
        else:
            elem_1_name = elem_1_k
        
        elem_2 = self.im.get(elem_2_k)
        if elem_2:
            elem_2_name = f"{elem_2.class_} ({elem_2.user_friendly_name})" if elem_2_k[0:4] == "elem" else f"<'{elem_2_k}' not found>"
        else:
            elem_2_name = elem_2_k
        
        assoc_name = str(a)

        return f"{elem_1_name:<50s} {assoc_name:<60s} {elem_2_name:<30s}"

    def pretty_ub_vals_attr(self, attr_and_val: list[AttrAndValues]) -> str:
        """Returns a string containg a human-readable name of the element, the value and the
           attribute relationship.
        """
        (elem_k, _), a, (ubval_k, _) = attr_and_val

        elem_1 = self.im.get(elem_k)
        if elem_1:
            elem_1_name = f"{elem_1.class_} ({elem_1.user_friendly_name})" if elem_k[0:4] == "elem" else f"<'{elem_k}' not found>"
        else:
            elem_1_name = elem_k

        attr_name = str(a)

        val_name = str(ubval_k)

        return f"{elem_1_name:<50s} {attr_name:<60s} {val_name:<30s}"

    def thin_ub_elems_and_assoc(self, ctx: Context, ub_elems_and_assoc: list[AssocAndElems]):
        if not ub_elems_and_assoc:
            return []

        (_, elem_1_v), a, (_, elem_2_v) = assoc = ub_elems_and_assoc[0]
        assoc_rel = ctx.assoc_rel(elem_1_v, a, elem_2_v)

        # Add negated constraint
        ctx.solver.push()

        print(f"\tAdd constraint Not({self.pretty_ub_elems_assoc(assoc)})")
        ctx.solver.add(Not(assoc_rel))
        
        res = ctx.solver.check()
        
        if res == sat:
            print("SAT:\tAdding one more constraint and trying again")
            # Get new ub_elems_and_assoc
            model = ctx.solver.model()
            thinned_ub_elems_and_assoc = self.get_ub_elems_and_assoc(ctx, model)
            
            # Print table showing the diff
            from difflib import context_diff
            uvar_as_text = lambda input: [self.pretty_ub_elems_assoc(assoc) for assoc in input]
            print("\n".join([a for a in context_diff(uvar_as_text(ub_elems_and_assoc), uvar_as_text(thinned_ub_elems_and_assoc), lineterm="", fromfile='Before', tofile="After")]))

            # Iterate
            return self.thin_ub_elems_and_assoc(ctx, thinned_ub_elems_and_assoc)
        else:
            print("UNSAT\tLast constraint was the association we are looking for!")
            ctx.solver.pop()
            
            if ub_elems_and_assoc[1:]:
                print("\tIterating over")
                print("\t\t" + "\n\t\t".join([self.pretty_ub_elems_assoc(assoc) for assoc in ub_elems_and_assoc[1:]]))
            return [*set([assoc] + self.thin_ub_elems_and_assoc(ctx, ub_elems_and_assoc[1:]))]

    def thin_ub_vals_and_attr(self, ctx: Context, ub_vals_and_attr: list[AttrAndValues]):
        if not ub_vals_and_attr:
            return []

        (_, elem_v), a, (_, attr_v) = attr = ub_vals_and_attr[0]
        attr_rel = ctx["attr_rel"](elem_v, a, attr_v)

        # Add negated constraint
        ctx.solver.push()

        print(f"\tAdd constraint Not({self.pretty_ubvals_attrs(attr)})")
        ctx.solver.add(Not(attr_rel))
        
        res = ctx.solver.check()
        
        if res == sat:
            print("SAT:\tAdding one more constraint and trying again")
            # Get new ub_elems_and_assoc
            model = ctx.solver.model()
            thinned_ub_vals_and_attr = self.get_ubvals_and_attr(ctx, model)
            
            # Print table showing the diff
            from difflib import context_diff
            uvar_as_text = lambda input: [self.pretty_ubvals_attrs(attr) for attr in input]
            print("\n".join([a for a in context_diff(uvar_as_text(ub_vals_and_attr), uvar_as_text(thinned_ub_vals_and_attr), lineterm="", fromfile='Before', tofile="After")]))

            # Iterate
            return self.thin_ub_vals_and_attr(ctx, thinned_ub_vals_and_attr)
        else:
            print("UNSAT\tLast constraint was the attribute we are looking for!")
            ctx.solver.pop()
            
            if ub_vals_and_attr[1:]:
                print("\tIterating over")
                print("\t\t" + "\n\t\t".join([self.pretty_ubvals_attrs(attr) for attr in ub_vals_and_attr[1:]]))
            return [*set([attr] + self.thin_ub_vals_and_attr(ctx, ub_vals_and_attr[1:]))]
