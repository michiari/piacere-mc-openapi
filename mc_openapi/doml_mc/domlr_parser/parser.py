import os
import re
from typing import Callable

import yaml
from lark import Lark, Transformer, UnexpectedCharacters
from mc_openapi.doml_mc.domlr_parser.exceptions import RequirementBadSyntaxException
from mc_openapi.doml_mc.domlr_parser.utils import (RefHandler, StringValuesCache,
                                                 VarStore)
from mc_openapi.doml_mc.error_desc_helper import get_user_friendly_name
from mc_openapi.doml_mc.imc import (Requirement, RequirementStore, SMTEncoding,
                                    SMTSorts)
from mc_openapi.doml_mc.intermediate_model import IntermediateModel
from z3 import And, Exists, ExprRef, ForAll, Implies, Not, Or, Solver, Xor, simplify


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
    def __init__(self, grammar: str = PARSER_DATA.grammar):
        self.parser = Lark(grammar, start="requirements")

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

            transformer = DOMLRTransformer(const_store, user_values_cache)

            return RequirementStore(transformer.transform(self.tree)), user_values_cache.get_list()
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

    # def relationship_expr(self, args):
    #     print(args)
    #     rel_name = args[1].value

    #     def _gen_rel_expr(enc: SMTEncoding, sorts: SMTSorts):
    #         rel, rel_type = RefHandler.get_relationship(enc, rel_name)
            
    #         if rel_type == RefHandler.ASSOCIATION:
    #             self.const_store.use(args[0].value)
    #             self.const_store.use(args[2].value)

    #             return RefHandler.get_association_rel(
    #                 enc,
    #                 RefHandler.get_const(args[0].value, sorts),
    #                 rel,
    #                 RefHandler.get_const(args[2].value, sorts)
    #             )
    #         elif rel_type == RefHandler.ATTRIBUTE:
    #             self.const_store.use(args[0].value)

    #             return RefHandler.get_attribute_rel(
    #                 enc,
    #                 RefHandler.get_const(args[0].value, sorts),
    #                 rel,
    #                 args[2](enc, sorts)
    #             )
    #         else:
    #             raise f"Error parsing relationship {rel_name}"
        
    #     return _gen_rel_expr

    def rel_elem_expr(self, args):
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