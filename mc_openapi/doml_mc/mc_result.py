from enum import Enum
from typing import Literal
from z3 import CheckSatResult, sat, unsat, unknown


class MCResult(Enum):
    sat = 1
    unsat = 2
    dontknow = 3

    @staticmethod
    def from_z3result(z3res: CheckSatResult, flipped: bool = False) -> "MCResult":
        """Returns an Enum which is either sat, unsat or dontknow.
        If flipped is true, then the sat and unsat are swapped: it's useful when
        we are evaluating an expression in negative form.
        """
        if flipped:
            if z3res == sat:
                return MCResult.unsat
            elif z3res == unsat:
                return MCResult.sat
        else:
            if z3res == sat:
                return MCResult.sat
            elif z3res == unsat:
                return MCResult.unsat

        assert z3res == unknown
        return MCResult.dontknow


class MCResults:
    DONTKNOW_MSG = "Timed out: unable to check some requirements."

    def __init__(self, results: list[tuple[MCResult, Literal["BUILTIN", "USER"], str]]):
        self.results = results

    def summarize(self) -> tuple[MCResult, str]:
        some_unsat = any(res == MCResult.unsat for res, _, _ in self.results)
        some_dontknow = any(
            res == MCResult.dontknow for res, _, _ in self.results)

        if some_unsat:
            builtin_err_msgs = [
                msg for res, type, msg in self.results if res == MCResult.unsat and type == "BUILTIN"]
            user_err_msgs = [
                msg for res, type, msg in self.results if res == MCResult.unsat and type == "USER"]

            # Print to text (instead of HTML)
            builtin_err_msg = "\n".join(builtin_err_msgs)
            user_err_msg = ""
            for req_desc, err, notes in user_err_msgs:
                user_err_msg += req_desc + '\n'
                user_err_msg += err + '\n'
                user_err_msg += "\n\t".join(notes)

            err_msg = ""
            if builtin_err_msgs:
                err_msg += '[Built-in]\n' + builtin_err_msg
            if user_err_msgs:
                err_msg += '\n[User]\n' + user_err_msg

            if some_dontknow:
                err_msg += '\n' + MCResults.DONTKNOW_MSG
            return MCResult.unsat, err_msg
        elif some_dontknow:
            return MCResult.dontknow, MCResults.DONTKNOW_MSG
        else:
            return MCResult.sat, "All requirements are satisfied."

    def add_results(self, results: "MCResults"):
        self.results.extend(results.results)
