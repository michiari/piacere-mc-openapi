import datetime
import copy
from pyecore.resources import ResourceSet, URI
from mc_openapi.string_uri import StringURI

def get_rset():
    if get_rset.doml_rset is None:
        rset = ResourceSet()
        resource = rset.get_resource(URI("mc_openapi/doml/doml.ecore"))
        doml_metamodel = resource.contents[0]

        rset.metamodel_registry[doml_metamodel.nsURI] = doml_metamodel
        for subp in doml_metamodel.eSubpackages:
            rset.metamodel_registry[subp.nsURI] = subp

        get_rset.doml_rset = rset

    assert get_rset.doml_rset is not None
    return copy.copy(get_rset.doml_rset)
get_rset.doml_rset = None

def make_error(user_msg, debug_msg=None):
    result = { "message": user_msg, "timestamp": datetime.datetime.now() }
    if debug_msg is not None:
        result["debug_message"] = debug_msg
    return result

def post(body, requirement=None):
    doml_xmi = body
    try:
        rset = get_rset()
        doml_uri = StringURI("user_doml", text=doml_xmi)
        resource = rset.create_resource(doml_uri)
        resource.load()
        doml = resource.contents[0]

        if doml.infrastructure.nodes[0].machineDefinition.ifaces[0].belongsTo is None:
            return { "result": "unsat",
                     "description": "Virtual machine is not linked to any network." }

        return  { "result": "sat" }

    except Exception as e:
        return make_error("Supplied with malformed DOML XMI model.", debug_msg=str(e)), 400
