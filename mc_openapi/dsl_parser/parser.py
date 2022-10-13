from asyncio import constants
from dataclasses import dataclass
from typing import Callable
from lark import Lark, Transformer
from mc_openapi.doml_mc.imc import Requirement, RequirementStore, SMTEncoding, SMTSorts
from z3 import Not, And, Or, Xor, Implies, Exists, ForAll, BoolRef, Solver
from mc_openapi.doml_mc.intermediate_model import IntermediateModel
from mc_openapi.doml_mc.error_desc_helper import get_user_friendly_name
from mc_openapi.dsl_parser.utils import RefHandler, UniqueVarStore

import os

class ParserData:
    def __init__(self) -> None:
        grammar_path = os.path.join(os.path.dirname(__file__), "grammar.lark")
        with open(grammar_path, "r") as grammar:
            self.grammar = grammar.read()

class Parser:
    def __init__(self, encodings: SMTEncoding, sorts: SMTSorts, grammar: str = ParserData().grammar):
        self.parser = Lark(grammar, start="start")
        self.encodings = encodings
        self.sorts = sorts

    def parse(self, input: str) -> RequirementStore:
        self.tree = self.parser.parse(input)

        constants_store = UniqueVarStore(self.encodings, self.sorts.element_sort)
        values_store = UniqueVarStore(self.encodings, self.sorts.attr_data_sort)
        ref_handler = RefHandler(self.encodings)

        transformer = DSLTransformer(constants_store, values_store, ref_handler)

        return RequirementStore(transformer.transform(self.tree))

class DSLTransformer(Transformer):
    def __init__(self, 
        constants_store: UniqueVarStore,  
        values_store: UniqueVarStore,
        ref_handler: RefHandler,
        visit_tokens: bool = True
    ) -> None:
        super().__init__(visit_tokens)
        self.constants_store = constants_store
        self.values_store = values_store
        self.ref_handler = ref_handler

    # These callbacks will be called when a rule with the same name
    # is matched. It starts from the leaves.

    def start(self, args):
        def flatten(items):
            return sum(map(flatten, items), []) if isinstance(items, list) else [items]
        # flatten the requirement list, otherwise we get nested lists
        # like [a, [b, [c, ...]]]
        return flatten(args)

    def __default__(self, data, children, meta):
        # print("DATA", data)
        # print("CHILDREN", children)
        # print("META", meta)
        return children

    def requirements(self, args):
        
        return args

    def requirement(self, args):
        name: str = args[0]
        expr: BoolRef = args[1]
        errd: Callable = args[2]
        return [Requirement(
            lambda enc, sort: expr,
            name.lower().replace(" ", "_"),
            name,
            errd
        )]

    def req_name(self, args):
        return str(args[0].value.replace('"', ''))
    
    def expression(self, args):
        return args[0]

    def binary_op_exp(self, args):
        return args[0]

    def consts(self, args):
        return [self.constants_store.use(arg.value) for arg in args]

    def negation(self, args):
        return Not(args[1])

    def double_implication(self, args):        
        return args[0] == args[2]
    
    def implication(self, args):        
        return Implies(args[0], args[2])

    def and_or_xor_exp(self, args):        
        op = args[1].value
        a = args[0]
        b = args[2]

        if op == "and":
            return And(a, b)
        elif op == "or":
            return Or(a, b)
        else: # xor
            return Xor(a, b)

    def quantification(self, args):
        quantifier = args[0].value

        bound_vars = args[1] # list of consts
        self.constants_store.quantify(bound_vars)

        if quantifier == "exists":
            return Exists(bound_vars, args[2])
        else: # forall
            return ForAll(bound_vars, args[2])


    def association_expr(self, args):
        const1 = self.constants_store.use(args[0].value)
        assoc  = self.ref_handler.get_association(args[2].value)
        const2 = self.constants_store.use(args[3].value)
        
        return self.ref_handler.get_association_rel(const1, assoc, const2)

    def attribute_expr(self, args):
        const = self.constants_store.use(args[0].value)
        assoc  = self.ref_handler.get_attribute(args[2].value)
        value = self.values_store.use(args[3].value)
        return self.ref_handler.get_attribute_rel(const, assoc, value)

    def equal(self, args):
        return args[0] == args[2]

    def not_equal(self, args):
        return args[0] != args[2]

    def class_or_const(self, args):
        if args[0].type == "CONST":
            _const = self.constants_store.use(args[0].value)
            return self.ref_handler.get_element_class(_const)
        elif args[0].type == "CLASS":
            return self.ref_handler.get_class(args[0].value)
    
    def error_desc(self, args):
        def err_callback(
            solver: Solver,
            smtsorts: SMTSorts,
            intermediate_model: IntermediateModel
        ) -> str:
            msg: str = args[0].value.replace('"', '')
            consts = self.constants_store.get_free_vars()
            model = solver.model()
            for const in consts:
                name = get_user_friendly_name(intermediate_model, model, const)
                msg = msg.replace("{" + str(const) + "}", f"'{name}'")
            return msg
        return err_callback

