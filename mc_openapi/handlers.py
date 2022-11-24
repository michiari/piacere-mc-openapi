import datetime
from .doml_mc import ModelChecker, MCResult


def make_error(user_msg, debug_msg=None):
    result = {"message": user_msg, "timestamp": datetime.datetime.now()}
    if debug_msg is not None:
        result["debug_message"] = debug_msg
        print(f"ERROR [{datetime.datetime.now()}]: {debug_msg}")
    return result


def post(body):
    doml_xmi = body
    try:
        dmc = ModelChecker(doml_xmi)
        results = dmc.check_requirements(threads=2, consistency_checks=False, timeout=50)
        res, msg = results.summarize()

        if res == MCResult.sat:
            return {"result": "sat"}
        else:
            return {"result": res.name,
                    "description": msg}

    # TODO: Make noteworthy exceptions to at least tell the user what is wrong
    except Exception as e:
        return make_error("The supplied DOMLX model is malformed or its DOML version is unsupported.", debug_msg=str(e)), 400
