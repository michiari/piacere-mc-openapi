import os
import re
from typing import Callable

import yaml
from lark import Lark, Transformer, UnexpectedCharacters
from mc_openapi.doml_mc.domlr_parser.exceptions import RequirementBadSyntaxException
from mc_openapi.doml_mc.domlr_parser.utils import (RefHandler, StringValuesCache, SynthesisRefHandler,
                                                 VarStore)
from mc_openapi.doml_mc.error_desc_helper import get_user_friendly_name
from mc_openapi.doml_mc.imc import (Requirement, RequirementStore, SMTEncoding,
                                    SMTSorts)
from mc_openapi.doml_mc.intermediate_model import IntermediateModel
from z3 import And, Exists, ExprRef, ForAll, Implies, Not, Or, Solver, Xor, simplify
from doml_synthesis import State

class ParserData:
    def __init__(self) -> None:
        # TODO: Replace with files api?
        grammar_path = os.path.join(os.path.dirname(__file__), "grammar.lark")
        exceptions_path = os.path.join(os.path.dirname(__file__), "exceptions.yaml")
        with open(grammar_path, "r") as grammar:
            self.grammar = grammar.read()
        with open(exceptions_path, "r") as exceptions:
            self.exceptions = yaml.safe_load(exceptions)

PARSER_DATA = ParserData()

class Parser:
    def __init__(self, transformer, grammar: str = PARSER_DATA.grammar):
        self.parser = Lark(grammar, start="requirements")
        self.transformer = transformer

    def parse(self, input: str):
        """Parse the input string containing the DOMLR requirements and
           returns a tuple with:
           - RequirementStore with the parsed requirements inside
           - A list of strings to be added to the string constant EnumSort
        """
        try:
            self.tree = self.parser.parse(input)

            const_store = VarStore()
            user_values_cache = StringValuesCache()

            transformer = self.transformer(const_store, user_values_cache)

            if isinstance(self.transformer, DOMLRTransformer):
                return (
                    RequirementStore(transformer.transform(self.tree)), 
                    user_values_cache.get_list()
                )
            else:
                reqs = transformer.transform(self.tree)

                # This function has to return state or it will break the
                # synthesis solver
                def user_reqs(state: State):
                    for (req, id, negated) in reqs:
                        state.solver.assert_and_track(
                            req(state) if not negated else Not(req(state)), f'Requirement {id}')
                    return state

                return user_reqs, user_values_cache.get_list()

        except UnexpectedCharacters as e:
            ctx = e.get_context(input)
            msg = _get_error_desc_for_unexpected_characters(e, input)

            # TODO: Replace before production
            print(msg)

            exit()
            # print()
            # print()
            # raise RequirementBadSyntaxException(e.line, e.column, msg)       

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
    def requirements(self, args) -> list[Requirement]:
        return args

    def requirement(self, args) -> Requirement:
        flip_expr: bool = args[0].value == "-"
        name: str = args[1]
        expr: Callable[[SMTEncoding, SMTSorts], ExprRef] = args[2]
        errd: Callable[[Solver, SMTSorts, IntermediateModel, int], str] = args[3]
        index = self.const_store.get_index_and_push()
        return Requirement(
            expr,
            name.lower().replace(" ", "_"),
            name,
            lambda solver, sorts, model: errd(
                solver, sorts, model, 
                index, 
                name
            ),
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
                print(
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
            arg1_ret = lambda enc, _: RefHandler.get_class(enc, arg1.value)
        else:
            arg1_ret = lambda enc, sorts: RefHandler.get_element_class(enc, RefHandler.get_const(arg1.value, sorts))

        if arg2.type == "CLASS":
            arg2_ret = lambda enc, _: RefHandler.get_class(enc, arg2.value)
        else:
            arg2_ret = lambda enc, sorts: RefHandler.get_element_class(enc, RefHandler.get_const(arg2.value, sorts))

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
            msg: str = f"[Requirement \"{requirement_desc}\"]"
            msg += "\n\t" + args[0].value.replace('"', '')
            # Get list of free variables
            consts_name = self.const_store.get_free_vars(index)
            consts = RefHandler.get_consts(consts_name, sorts)
            notes = ""
            try:
                model = solver.model()
                for const in consts:
                    name = get_user_friendly_name(intermediate_model, model, const)
                    msg = msg.replace("{" + str(const) + "}", f"'{name}'")
            except:
                notes += "\n\t- model not found: it's not possible to show which element is causing the issue"

            # tell the user which variables are not free
            unused_free_vars = re.findall(r"{[^{}]*}", msg)
            if unused_free_vars:
                notes += "\n\t- The following variables are not free and should be removed from the error description:"
                notes += "\n\t" + " ".join(unused_free_vars)

            return msg + ("\n\n\tNOTES:" + notes if notes else "")
        return err_callback

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
        # TODO: Transform Requirement into 
        return args

    def requirement(self, args) -> tuple:
        flip_expr: bool = args[0].value == "-"
        name: str = args[1]
        expr: Callable[[State], ExprRef] = args[2]
        return (
            expr,
            name.lower().replace(" ", "_"), # id
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
            arg1_ret = lambda state: SynthesisRefHandler.get_class(state, arg1.value)
        else:
            arg1_ret = lambda state: SynthesisRefHandler.get_element_class(state, SynthesisRefHandler.get_const(arg1.value, state))

        if arg2.type == "CLASS":
            arg2_ret = lambda state: SynthesisRefHandler.get_class(state, arg2.value)
        else:
            arg2_ret = lambda state: SynthesisRefHandler.get_element_class(state, SynthesisRefHandler.get_const(arg2.value, state))

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

def _get_error_desc_for_unexpected_characters(e: UnexpectedCharacters, input: str):
    # Error description
    msg = "Syntax Error:\n\n"
    msg += e.get_context(input)
    msg += "Expected one of the following:\n"
    for val in e.allowed:
        val = PARSER_DATA.exceptions["TOKENS"].get(val, "")
        msg += (f"• {val}\n")
    # Suggestion that might be useful
    if e.char == ".":
        msg += "HINTS:\n"
        msg += PARSER_DATA.exceptions["HINTS"]["DOT"]
    # Print line highlighting the error

    return msg