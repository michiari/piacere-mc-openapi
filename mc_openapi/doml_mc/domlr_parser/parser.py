import os

import yaml
from doml_synthesis import State
from lark import Lark, UnexpectedCharacters, UnexpectedEOF
from z3 import Not

from mc_openapi.doml_mc.domlr_parser.exceptions import \
    RequirementBadSyntaxException
from mc_openapi.doml_mc.domlr_parser.utils import StringValuesCache, VarStore
from mc_openapi.doml_mc.imc import RequirementStore

class ParserData:
    def __init__(self) -> None:
        grammar_path = os.path.join(os.path.dirname(__file__), "grammar.lark")
        exceptions_path = os.path.join(
            os.path.dirname(__file__), "exceptions.yaml")
        with open(grammar_path, "r") as grammar:
            self.grammar = grammar.read()
        with open(exceptions_path, "r") as exceptions:
            self.exceptions = yaml.safe_load(exceptions)


PARSER_DATA = ParserData()


class Parser:
    def __init__(self, transformer, grammar: str = PARSER_DATA.grammar):
        self.parser = Lark(grammar, start="start", parser="lalr")
        self.transformer = transformer

    def parse(self, input: str, for_synthesis: bool = False) -> tuple[RequirementStore, list[str], dict[str, bool]]:
        """Parse the input string containing the DOMLR requirements and
           returns a tuple with:
           - RequirementStore with the parsed requirements inside
           - A list of strings to be added to the string constant EnumSort
           - A dictionary of all the flags
        """
        try:
            self.tree = self.parser.parse(input)

            const_store = VarStore()
            user_values_cache = StringValuesCache()

            transformer = self.transformer(const_store, user_values_cache)

            if not for_synthesis:
                reqs, flags = transformer.transform(self.tree)
                return (
                    RequirementStore(reqs),
                    user_values_cache.get_list(),
                    flags
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

        except UnexpectedEOF as e:
            msg = "Unexpected End of File:\n"
            msg += "Did you forget the `error:` keyword at the end of a requirement?"
            raise Exception(msg)

        except UnexpectedCharacters as e:
            msg = _get_error_desc_for_unexpected_characters(e, input)
            raise RequirementBadSyntaxException(e.line, e.column, msg)

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
