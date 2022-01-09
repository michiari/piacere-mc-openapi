import datetime

def make_error(user_msg, debug_msg=None):
    result = { "message": user_msg, "timestamp": datetime.now() }
    if debug_msg is not None:
        result["debug_message"] = debug_msg
    return result

def post(body):
    if "model" not in body:
        return make_error("Model to be checked is missing."), 400

    doml = body["model"]

    if doml["typeId"] != "commons_DOMLModel":
        return make_error("Not a DOML model."), 400

    apps = doml["application"][0]["children"]
    for app in apps:
        if "exposedInterfaces" in app:
            for intf in app["exposedInterfaces"]:
                if "endPoint" in intf and intf["endPoint"] == "80":
                    return { "result": "unsat",
                             "description": "Endpoint on default HTTP port 80." }

    return  { "result": "sat" }
