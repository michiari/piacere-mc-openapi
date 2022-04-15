import datetime
from z3 import sat, unsat
from .doml_mc import ModelChecker


def make_error(user_msg, debug_msg=None):
    result = {"message": user_msg, "timestamp": datetime.datetime.now()}
    if debug_msg is not None:
        result["debug_message"] = debug_msg
    return result


def post(body, requirement=None):
    doml_xmi = body
    try:
        dmc = ModelChecker(doml_xmi)
        dmc.add_common_requirements()

        result = dmc.check()

        if result == sat:
            return {"result": "sat"}
        elif result == unsat:
            return {"result": "unsat",
                    "description": "Virtual machine is not linked to any network."}
        else:
            return {"result": "dontknow"}

    except Exception as e:
        return make_error("Supplied with malformed DOML XMI model.", debug_msg=str(e)), 400
