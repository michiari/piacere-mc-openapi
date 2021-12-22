import datetime

def make_error(user_msg, debug_msg=None):
    result = { "message": user_msg, "timestamp": datetime.now() }
    if debug_msg is not None:
        result["debug_message"] = debug_msg
    return result

def post(body):
    if body["model"] is None:
        return make_error("Model to be checked is missing."), 400
    return  { "result": "dontknow" }
