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
        self.parser = Lark(grammar, start="requirements")

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

    def __default__(self, data, children, meta):
        return children

    # start
    def requirements(self, args) -> list[Requirement]:
        return args

    def requirement(self, args) -> Requirement:
        name: str = args[0]
        expr: Callable[[SMTEncoding, SMTSorts], ExprRef] = args[1]
        errd: Callable[[Solver, SMTSorts, IntermediateModel, int], str] = args[2]
        return Requirement(
            expr,
            name.lower().replace(" ", "_"),
            name,
            lambda solver, sorts, model: errd(solver, sorts, model, self.const_store.get_index_and_push())
        )

    def req_name(self, args) -> str:
        return str(args[0].value.replace('"', ''))

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
        return lambda enc, sorts: And(args[0](enc, sorts), args[1](enc, sorts))

    def or_expr(self, args):
        return lambda enc, sorts: Or(args[0](enc, sorts), args[1](enc, sorts))

    def exists(self, args):
        return lambda enc, sorts: Exists(args[0](enc, sorts), args[1](enc, sorts))

    def forall(self, args):
        return lambda enc, sorts: ForAll(args[0](enc, sorts), args[1](enc, sorts))

    def association_expr(self, args):
        self.const_store.use(args[0].value)
        self.const_store.use(args[2].value)
        return lambda enc, sorts: RefHandler.get_association_rel(
            enc,
            RefHandler.get_const(args[0].value, sorts),
            RefHandler.get_association(enc, args[1].value),
            RefHandler.get_const(args[2].value, sorts)
        )

    def attribute_expr(self, args):
        self.const_store.use(args[0].value)
        return lambda enc, sorts: RefHandler.get_attribute_rel(
            enc,
            RefHandler.get_const(args[0].value, sorts),
            RefHandler.get_attribute(enc, args[1].value),
            RefHandler.get_value(args[2].value, sorts)
        )

    def equality(self, args):
        return lambda enc, sorts: args[0](enc, sorts) == args[1](enc, sorts)

    def inequality(self, args):
        return lambda enc, sorts: args[0](enc, sorts) != args[1](enc, sorts)

    def const_or_class(self, args):
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
