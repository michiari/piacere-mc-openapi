import logging
import re
from collections import ChainMap
from typing import Callable, Literal

from lark import Transformer
from z3 import And, Exists, ExprRef, ForAll, Implies, Not, Or, Solver

from mc_openapi.doml_mc.domlr_parser.utils import (RefHandler,
                                                   StringValuesCache, VarStore)
from mc_openapi.doml_mc.error_desc_helper import get_user_friendly_name
from mc_openapi.doml_mc.imc import Requirement, SMTEncoding, SMTSorts
from mc_openapi.doml_mc.intermediate_model.doml_element import \
    IntermediateModel


class DOMLRTransformer(Transformer):
    # These callbacks will be called when a rule with the same name
    # is matched. It starts from the leaves.
    def __init__(self,
                 const_store: VarStore,
                 user_values_cache: StringValuesCache,
                 visit_tokens: bool = True
                 ) -> None:
        super().__init__(visit_tokens)
        self.const_store = const_store
        self.user_values_cache = user_values_cache

    def __default__(self, data, children, meta):
        return children

    # start
    def start(self, args) -> tuple[list[Requirement], dict[str, str]]:
        if not isinstance(args[0], dict): # there aren't flags
            args = [{}, args[0]]
        return args[1], args[0]
    
    def flags(self, args) -> dict:
        return dict(ChainMap(*list(args)))

    def flag_requirement_check(self, args) -> dict:
        return { args[0].value : True }

    def flag_requirement_check_consistency(self, args) -> dict:
        return { '_check_consistency' : True }

    def flag_requirement_ignore(self, args) -> dict:
        return { args[0].value : False }

    def flag_requirement_ignore_builtin(self, args) -> dict:
        return { '_ignore_builtin' : True }

    def flag_csp(self, args) -> dict:
        return { '_csp' : True }

    def requirements(self, args) -> list[Requirement]:
        return args

    def requirement(self, args) -> Requirement:
        flip_expr: bool = args[0].value == "-"
        name: str = args[1]
        expr: Callable[[SMTEncoding, SMTSorts], ExprRef] = args[2]
        errd: tuple[Literal["USER", "BUILTIN"], Callable[[Solver, SMTSorts,
                                                          IntermediateModel, int], str]] = args[3]
        index = self.const_store.get_index_and_push()
        return Requirement(
            expr,
            name.lower().replace(" ", "_"),
            name,
            (errd[0], lambda solver, sorts, model: errd[1](
                solver, sorts, model,
                index,
                name
            )),
            flipped=flip_expr
        )

    def req_name(self, args) -> str:
        return str(args[0].value.replace('"', ''))

    # Requirement requirement expression

    def bound_consts(self, args):
        const_names = list(map(lambda arg: arg.value, args))
        for name in const_names:
            self.const_store.use(name)
            self.const_store.quantify(name)
        return lambda _, sorts: RefHandler.get_consts(const_names, sorts)

    def negation(self, args):
        return lambda enc, sorts: Not(args[0](enc, sorts))

    def iff_expr(self, args):
        return lambda enc, sorts: args[0](enc, sorts) == args[1](enc, sorts)

    def implies_expr(self, args):
        return lambda enc, sorts: Implies(args[0](enc, sorts), args[1](enc, sorts))

    def and_expr(self, args):
        return lambda enc, sorts: And([arg(enc, sorts) for arg in args])

    def or_expr(self, args):
        return lambda enc, sorts: Or([arg(enc, sorts) for arg in args])

    def exists(self, args):
        return lambda enc, sorts: Exists(args[0](enc, sorts), args[1](enc, sorts))

    def forall(self, args):
        return lambda enc, sorts: ForAll(args[0](enc, sorts), args[1](enc, sorts))

    def rel_assoc_expr(self, args):
        """An ASSOCIATION relationship"""
        rel_name = args[1].value
        self.const_store.use(args[0].value)
        self.const_store.use(args[2].value)

        def _gen_rel_elem_expr(enc: SMTEncoding, sorts: SMTSorts):
            rel, rel_type = RefHandler.get_relationship(enc, rel_name)

            assert rel_type == RefHandler.ASSOCIATION

            return RefHandler.get_association_rel(
                enc,
                RefHandler.get_const(args[0].value, sorts),
                rel,
                RefHandler.get_const(args[2].value, sorts)
            )
        return _gen_rel_elem_expr

    def rel_attr_value_expr(self, args):
        """An ATTRIBUTE relationship with a rhs that is a value"""

        rel_name = args[1].value

        def _gen_rel_attr_value_expr(enc: SMTEncoding, sorts: SMTSorts):
            elem = RefHandler.get_const(args[0].value, sorts)
            rel, rel_type = RefHandler.get_relationship(enc, rel_name)
            assert rel_type == RefHandler.ATTRIBUTE

            rhs_value, rhs_value_type = args[3]
            rhs_value = rhs_value(enc, sorts)
            op = args[2].value

            if rhs_value_type == RefHandler.INTEGER:

                lhs_value = RefHandler.get_value("x", sorts)

                return And(
                    RefHandler.get_attribute_rel(enc,
                                                 elem,
                                                 rel,
                                                 lhs_value
                                                 ),
                    self.compare_int(sorts, op, lhs_value, rhs_value)
                )
            elif rhs_value_type == RefHandler.STRING or rhs_value_type == RefHandler.BOOLEAN:
                expr = RefHandler.get_attribute_rel(enc,
                                                    elem,
                                                    rel,
                                                    rhs_value
                                                    )
                if op == "==":
                    return expr
                elif op == "!=":
                    return Not(expr)
                else:
                    raise f'Invalid compare operator "{op}". It must be "==" or "!=".'

        return _gen_rel_attr_value_expr

    def rel_attr_elem_expr(self, args):
        """An ATTRIBUTE relationship with a rhs that is another element"""

        rel1_name = args[1].value
        rel2_name = args[4].value
        op = args[2].value

        def _gen_rel_attr_elem_expr(enc: SMTEncoding, sorts: SMTSorts):
            elem1 = RefHandler.get_const(args[0].value, sorts)
            elem2 = RefHandler.get_const(args[3].value, sorts)
            rel1, rel1_type = RefHandler.get_relationship(enc, rel1_name)
            rel2, rel2_type = RefHandler.get_relationship(enc, rel2_name)

            assert rel1_type == RefHandler.ATTRIBUTE
            assert rel2_type == RefHandler.ATTRIBUTE

            rhs_value = RefHandler.get_value("x", sorts)

            expr = And(
                RefHandler.get_attribute_rel(enc,
                                             elem1,
                                             rel1,
                                             rhs_value
                                             ),
                RefHandler.get_attribute_rel(enc,
                                             elem2,
                                             rel2,
                                             rhs_value
                                             )
            )
            if op == "==":
                return expr
            elif op == "!=":
                return Not(expr)
            else:
                rhs1_value = RefHandler.get_value("rhs1", sorts)
                rhs2_value = RefHandler.get_value("rhs2", sorts)
                expr = And(
                    RefHandler.get_attribute_rel(enc,
                                                 elem1,
                                                 rel1,
                                                 rhs1_value
                                                 ),
                    RefHandler.get_attribute_rel(enc,
                                                 elem2,
                                                 rel2,
                                                 rhs2_value
                                                 ),
                    self.compare_int(sorts, op, rhs1_value, rhs2_value)
                )
                logging.warning(
                    "Warning: Comparing attributes of two elements with {op} is experimental!\n",
                    "Assumption: the attribute is an Integer."
                )
                return expr

        return _gen_rel_attr_elem_expr

    def _get_equality_sides(self, arg1, arg2):
        # We track use of const in const_or_class
        if arg1.type == "CONST" and arg2.type == "CONST":
            return (
                lambda _, sorts: RefHandler.get_const(arg1.value, sorts),
                lambda _, sorts: RefHandler.get_const(arg2.value, sorts)
            )

        if arg1.type == "CLASS":
            def arg1_ret(enc, _): return RefHandler.get_class(enc, arg1.value)
        else:
            def arg1_ret(enc, sorts): return RefHandler.get_element_class(
                enc, RefHandler.get_const(arg1.value, sorts))

        if arg2.type == "CLASS":
            def arg2_ret(enc, _): return RefHandler.get_class(enc, arg2.value)
        else:
            def arg2_ret(enc, sorts): return RefHandler.get_element_class(
                enc, RefHandler.get_const(arg2.value, sorts))

        return (arg1_ret, arg2_ret)

    def equality(self, args):
        a, b = self._get_equality_sides(args[0], args[1])
        return lambda enc, sorts: a(enc, sorts) == b(enc, sorts)

    def inequality(self, args):
        a, b = self._get_equality_sides(args[0], args[1])
        return lambda enc, sorts: a(enc, sorts) != b(enc, sorts)

    def const_or_class(self, args):
        if args[0].type == "CONST":
            self.const_store.use(args[0].value)
        return args[0]

    def compare_int(self, sorts: SMTSorts, op: str, a, b):
        # To extract the `int` contained in the attr_data_sort,
        # we need to call its `get_int` method on the `DatatypeRef`
        get_int = sorts.attr_data_sort.get_int

        a = get_int(a)
        b = get_int(b)

        if op == ">":
            return a > b
        if op == ">=":
            return a >= b
        if op == "<":
            return a < b
        if op == "<=":
            return a <= b
        if op == "==":
            return a == b
        if op == "!=":
            return a != b
        raise f"Invalid Compare Operator Symbol: {op}"

    def value(self, args):
        type = args[0].type
        value = args[0].value

        if type == "ESCAPED_STRING":
            value = value.replace('"', '')
            self.user_values_cache.add(value)
            return lambda enc, sorts: RefHandler.get_str(value, enc, sorts), RefHandler.STRING
        elif type == "NUMBER":
            return lambda _, sorts: RefHandler.get_int(value, sorts), RefHandler.INTEGER
        elif type == "BOOL":
            return lambda _, sorts: RefHandler.get_bool(value, sorts), RefHandler.BOOLEAN
        # elif type == "VALUE":
        #     return lambda _, sorts: RefHandler.get_value(value, sorts), RefHandler.VALUE_REF

    def error_desc(self, args):
        def err_callback(
            solver: Solver,
            sorts: SMTSorts,
            intermediate_model: IntermediateModel,
            index: int,
            requirement_desc: str
        ) -> str:
            err_msg = args[0].value.replace('"', '')
            # Get list of free variables
            consts_name = self.const_store.get_free_vars(index)
            consts = RefHandler.get_consts(consts_name, sorts)
            notes = []
            try:
                model = solver.model()
                for const in consts:
                    name = get_user_friendly_name(
                        intermediate_model, model, const)
                    err_msg = err_msg.replace(
                        "{" + str(const) + "}", f"'{name}'")
            except:
                notes.append(
                    "Model not found: it's not possible to show which element is causing the issue")

            # tell the user which variables are not free
            unused_free_vars = re.findall(r"{[^{}]*}", err_msg)
            if unused_free_vars:
                notes.append(
                    "The following variables are not free and should be removed from the error description: " + " ".join(unused_free_vars))

            return (requirement_desc, err_msg, notes)
        return ("USER", err_callback)
