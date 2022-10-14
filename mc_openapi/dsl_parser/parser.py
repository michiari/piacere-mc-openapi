from typing import Callable
from lark import Lark, Transformer
from mc_openapi.doml_mc.imc import Requirement, RequirementStore, SMTEncoding, SMTSorts
from z3 import Not, And, Or, Xor, Implies, Exists, ForAll, ExprRef, Solver
from mc_openapi.doml_mc.intermediate_model import IntermediateModel
from mc_openapi.doml_mc.error_desc_helper import get_user_friendly_name
from mc_openapi.dsl_parser.utils import RefHandler, VarStore

import os

class ParserData:
    def __init__(self) -> None:
        grammar_path = os.path.join(os.path.dirname(__file__), "grammar.lark")
        with open(grammar_path, "r") as grammar:
            self.grammar = grammar.read()

class Parser:
    def __init__(self, grammar: str = ParserData().grammar):
        self.parser = Lark(grammar, start="start")

    def parse(self, input: str) -> RequirementStore:
        self.tree = self.parser.parse(input)

        const_store = VarStore()

        transformer = DSLTransformer(const_store)

        return RequirementStore(transformer.transform(self.tree))

class DSLTransformer(Transformer):
    # These callbacks will be called when a rule with the same name
    # is matched. It starts from the leaves.
    def __init__(self, const_store: VarStore, visit_tokens: bool = True) -> None:
        super().__init__(visit_tokens)
        self.const_store = const_store

    def start(self, args):
        def flatten(items):
            return sum(map(flatten, items), []) if isinstance(items, list) else [items]
        # flatten the requirement list, otherwise we get nested lists
        # like [a, [b, [c, ...]]]
        return flatten(args)

    def __default__(self, data, children, meta):
        return children

    def requirements(self, args):
        
        return args

    def requirement(self, args):
        name: str = args[0]
        expr: Callable[[SMTEncoding, SMTSorts], ExprRef] = args[1]
        errd: Callable[[Solver, SMTSorts, IntermediateModel, int], str] = args[2]
        return [Requirement(
            expr,
            name.lower().replace(" ", "_"),
            name,
            lambda solver, sorts, model: errd(solver, sorts, model, self.const_store.get_index_and_push())
        )]

    def req_name(self, args):
        return str(args[0].value.replace('"', ''))
    
    def expression(self, args):
        return lambda enc, sorts: args[0](enc, sorts)

    def binary_op_exp(self, args):
        return lambda enc, sorts: args[0](enc, sorts)

    def bound_consts(self, args):
        const_names = list(map(lambda arg: arg.value, args))
        for name in const_names:
            self.const_store.use(name)
            self.const_store.quantify(name)
        return lambda _, sorts: RefHandler.get_consts(const_names, sorts)

    def negation(self, args):
        return lambda enc, sorts: Not(args[1](enc, sorts))

    def double_implication(self, args):        
        return lambda enc, sorts: args[0](enc, sorts) == args[2](enc, sorts)
    
    def implication(self, args):        
        return lambda enc, sorts: Implies(args[0](enc, sorts), args[2](enc, sorts))

    def and_or_xor_exp(self, args):        
        op = args[1].value
        a = args[0]
        b = args[2]

        if op == "and":
            return lambda enc, sorts: And(a(enc, sorts), b(enc, sorts))
        elif op == "or":
            return lambda enc, sorts: Or(a(enc, sorts), b(enc, sorts))
        else: # xor
            return lambda enc, sorts: Xor(a(enc, sorts), b(enc, sorts))

    def quantification(self, args):
        quantifier = args[0].value

        bound_vars = args[1] # lambda that return list of consts

        if quantifier == "exists":
            return lambda enc, sorts: Exists(bound_vars(enc, sorts), args[2](enc, sorts))
        else: # forall
            return lambda enc, sorts: ForAll(bound_vars(enc, sorts), args[2](enc, sorts))


    def association_expr(self, args):
        self.const_store.use(args[0].value)
        self.const_store.use(args[3].value)
        return lambda enc, sorts: RefHandler.get_association_rel(
            enc,
            RefHandler.get_const(args[0].value, sorts),
            RefHandler.get_association(enc, args[2].value),
            RefHandler.get_const(args[3].value, sorts)
        )

    def attribute_expr(self, args):
        return lambda enc, sorts: RefHandler.get_attribute_rel(
            enc,
            RefHandler.get_const(args[0].value, sorts),
            RefHandler.get_attribute(enc, args[2].value),
            RefHandler.get_value(args[3].value, sorts)
        )

    def equal(self, args):
        return lambda enc, sorts: args[0](enc, sorts) == args[2](enc, sorts)

    def not_equal(self, args):
        return lambda enc, sorts: args[0](enc, sorts) != args[2](enc, sorts)

    def class_or_const(self, args):
        if args[0].type == "CONST":
            self.const_store.use(args[0].value)
            return lambda enc, sorts: RefHandler.get_element_class(enc, RefHandler.get_const(args[0].value, sorts))
        elif args[0].type == "CLASS":
            return lambda enc, _: RefHandler.get_class(enc, args[0].value)
    
    def error_desc(self, args):
        def err_callback(
            solver: Solver,
            sorts: SMTSorts,
            intermediate_model: IntermediateModel,
            index
        ) -> str:
            msg: str = args[0].value.replace('"', '')
            consts_name = self.const_store.get_free_vars(index)
            consts = RefHandler.get_consts(consts_name, sorts)
            model = solver.model()
            for const in consts:
                name = get_user_friendly_name(intermediate_model, model, const)
                msg = msg.replace("{" + str(const) + "}", f"'{name}'")
            return msg
        return err_callback

