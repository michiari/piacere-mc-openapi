from typing import Callable

from doml_synthesis import State
from lark import Transformer
from z3 import And, Exists, ExprRef, ForAll, Implies, Not, Or

from mc_openapi.doml_mc.domlr_parser.utils import (StringValuesCache,
                                                   SynthesisRefHandler,
                                                   VarStore)


class SynthesisDOMLRTransformer(Transformer):
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
    def requirements(self, args) -> list[tuple]:
        return args

    def requirement(self, args) -> tuple:
        flip_expr: bool = args[0].value == "-"
        name: str = args[1]
        expr: Callable[[State], ExprRef] = args[2]
        return (
            expr,
            name.lower().replace(" ", "_"),  # id
            flip_expr
        )

    def req_name(self, args) -> str:
        return str(args[0].value.replace('"', ''))

    # Requirement requirement expression

    def bound_consts(self, args):
        const_names = list(map(lambda arg: arg.value, args))
        for name in const_names:
            self.const_store.use(name)
            self.const_store.quantify(name)
        return lambda state: SynthesisRefHandler.get_consts(const_names, state)

    def negation(self, args):
        return lambda state: Not(args[0](state))

    def iff_expr(self, args):
        return lambda state: args[0](state) == args[1](state)

    def implies_expr(self, args):
        return lambda state: Implies(args[0](state), args[1](state))

    def and_expr(self, args):
        return lambda state: And([arg(state) for arg in args])

    def or_expr(self, args):
        return lambda state: Or([arg(state) for arg in args])

    def exists(self, args):
        return lambda state: Exists(args[0](state), args[1](state))

    def forall(self, args):
        return lambda state: ForAll(args[0](state), args[1](state))

    def rel_assoc_expr(self, args):
        """An ASSOCIATION relationship"""
        rel_name = args[1].value
        self.const_store.use(args[0].value)
        self.const_store.use(args[2].value)

        def _gen_rel_elem_expr(state: State):
            rel = SynthesisRefHandler.get_assoc(state, rel_name)

            return state.rels.AssocRel(
                SynthesisRefHandler.get_const(args[0].value, state),
                rel.ref,
                SynthesisRefHandler.get_const(args[2].value, state)
            )
        return _gen_rel_elem_expr

    def rel_attr_value_expr(self, args):
        """An ATTRIBUTE relationship with a rhs that is a value

           CONST "has" RELATIONSHIP COMPARISON_OP value
           0           1            2             3
        """

        rel_name = args[1].value

        def _gen_rel_attr_value_expr(state: State):
            elem = SynthesisRefHandler.get_const(args[0].value, state)
            rel = SynthesisRefHandler.get_attr(state, rel_name)

            rhs_value, rhs_value_type = args[3]
            rhs_value = rhs_value(state)
            op = args[2].value

            if rhs_value_type == SynthesisRefHandler.INTEGER and rel.type == 'Integer':
                lhs_value = state.rels.int.AttrValueRel(elem, rel.ref)
                return And(
                    self.compare(op, lhs_value, rhs_value),
                    state.rels.int.AttrSynthRel(elem, rel.ref)
                )
            elif op != "==" and op != "!=":
                raise "You can only use == and != to compare Strings and Booleans!"
            elif rhs_value_type == SynthesisRefHandler.STRING:
                lhs_value = state.rels.str.AttrValueRel(elem, rel.ref)

                return And(
                    lhs_value == rhs_value if op == "==" else lhs_value != rhs_value,
                    state.rels.str.AttrSynthRel(elem, rel.ref)
                )
            elif rhs_value_type == SynthesisRefHandler.BOOLEAN:
                lhs_value = state.rels.bool.AttrValueRel(elem, rel.ref)
                return And(
                    lhs_value == rhs_value if op == "==" else lhs_value != rhs_value,
                    state.rels.bool.AttrSynthRel(elem, rel.ref)
                )
            else:
                raise f'Invalid value {rhs_value} during parsing for synthesis.'

        return _gen_rel_attr_value_expr

    def rel_attr_elem_expr(self, args):
        """An ATTRIBUTE relationship with a rhs that is another element
           CONST "has" RELATIONSHIP COMPARISON_OP CONST RELATIONSHIP
           0           1            2             3     4
        """

        rel1_name = args[1].value
        rel2_name = args[4].value
        op = args[2].value

        def _gen_rel_attr_elem_expr(state: State):
            elem1 = SynthesisRefHandler.get_const(args[0].value, state)
            elem2 = SynthesisRefHandler.get_const(args[3].value, state)
            rel1 = SynthesisRefHandler.get_attr(state, rel1_name)
            rel2 = SynthesisRefHandler.get_attr(state, rel2_name)

            if rel1.type == rel2.type == 'Integer':
                return And(
                    state.rels.int.AttrSynthRel(elem1, rel1.ref),
                    state.rels.int.AttrSynthRel(elem2, rel2.ref),
                    self.compare(
                        op,
                        state.rels.int.AttrValueRel(elem1, rel1.ref),
                        state.rels.int.AttrValueRel(elem2, rel2.ref)
                    )
                )
            if rel1.type == rel2.type == 'Boolean':
                return And(
                    state.rels.bool.AttrSynthRel(elem1, rel1.ref),
                    state.rels.bool.AttrSynthRel(elem2, rel2.ref),
                    self.compare(
                        op,
                        state.rels.bool.AttrValueRel(elem1, rel1.ref),
                        state.rels.bool.AttrValueRel(elem2, rel2.ref)
                    )
                )
            if rel1.type == rel2.type == 'String':
                return And(
                    state.rels.str.AttrSynthRel(elem1, rel1.ref),
                    state.rels.str.AttrSynthRel(elem2, rel2.ref),
                    self.compare(
                        op,
                        state.rels.str.AttrValueRel(elem1, rel1.ref),
                        state.rels.str.AttrValueRel(elem2, rel2.ref)
                    )
                )
            raise f'Attribute relationships {rel1_name} ({rel1.type}) and {rel2_name} ({rel2.type}) have mismatch type.'

        return _gen_rel_attr_elem_expr

    def _get_equality_sides(self, arg1, arg2):
        # We track use of const in const_or_class
        if arg1.type == "CONST" and arg2.type == "CONST":
            return (
                lambda state: SynthesisRefHandler.get_const(arg1.value, state),
                lambda state: SynthesisRefHandler.get_const(arg2.value, state)
            )

        if arg1.type == "CLASS":
            def arg1_ret(state): return SynthesisRefHandler.get_class(
                state, arg1.value)
        else:
            def arg1_ret(state): return SynthesisRefHandler.get_element_class(
                state, SynthesisRefHandler.get_const(arg1.value, state))

        if arg2.type == "CLASS":
            def arg2_ret(state): return SynthesisRefHandler.get_class(
                state, arg2.value)
        else:
            def arg2_ret(state): return SynthesisRefHandler.get_element_class(
                state, SynthesisRefHandler.get_const(arg2.value, state))

        return (arg1_ret, arg2_ret)

    def equality(self, args):
        a, b = self._get_equality_sides(args[0], args[1])
        return lambda state: a(state) == b(state)

    def inequality(self, args):
        a, b = self._get_equality_sides(args[0], args[1])
        return lambda state: a(state) != b(state)

    def const_or_class(self, args):
        if args[0].type == "CONST":
            self.const_store.use(args[0].value)
        return args[0]

    def compare(self, op: str, a, b):

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
            return lambda state: SynthesisRefHandler.get_str(value, state), SynthesisRefHandler.STRING
        elif type == "NUMBER":
            return lambda _: value, SynthesisRefHandler.INTEGER
        elif type == "BOOL":
            return lambda _: SynthesisRefHandler.get_bool(value), SynthesisRefHandler.BOOLEAN

