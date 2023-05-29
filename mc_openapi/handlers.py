import datetime
import logging
import os

from flask import render_template
from mc_openapi.doml_mc.html_output import html_template

from mc_openapi.doml_mc.intermediate_model.metamodel import DOMLVersion
from mc_openapi.doml_mc import verify_model, init_model, verify_csp_compatibility
from .doml_mc import MCResult


def make_error(user_msg, debug_msg=None):
    result = {"message": user_msg, "timestamp": datetime.datetime.now()}
    if debug_msg is not None:
        result["debug_message"] = debug_msg
        logging.error(debug_msg)
    return result


def modelcheck(body, version=None):
    return mc(body, version)

def modelcheck_html(body, version=None):
    return mc(body, version, isHtml=True)

def mc(body, version, isHtml = False):
    doml_xmi = body
    doml_version_str: str = None
    doml_version: DOMLVersion = None
    try:
        # First try to infer DOML version from ENV, then query params
        doml_version_str = os.environ.get("DOML_VERSION") or version
        
        if doml_version_str:
            doml_version = DOMLVersion.get(doml_version_str)
            logging.info(f"Forcing DOML {doml_version.value}")

        dmc = init_model(doml_xmi, doml_version)

        res, msg = verify_model(dmc)

        if isHtml:
            return html_template("DOML Model Checker - Results", "HELLO WORLD!")
        else:
            if res == MCResult.sat:
                return {
                    "result": "sat",
                    "doml_version": dmc.doml_version.value
                }
            else:
                return {
                    "result": res.name,
                    "doml_version": dmc.doml_version.value,
                    "description": f'[Using DOML {dmc.doml_version.value}]\n{msg}'
                }

    except Exception as e:
        return make_error("The supplied DOMLX model is malformed or its DOML version is unsupported.", debug_msg=str(e)), 400

def csp(body, version=None):
    doml_xmi = body
    doml_version_str: str = None
    doml_version: DOMLVersion = None
    try:
        # First try to infer DOML version from ENV, then query params
        doml_version_str = os.environ.get("DOML_VERSION") or version
        
        if doml_version_str:
            doml_version = DOMLVersion.get(doml_version_str)
            logging.info(f"Forcing DOML {doml_version.value}")

        dmc = init_model(doml_xmi, doml_version)
        
        # TODO: Do something with the results
        return verify_csp_compatibility(dmc)
    

    except Exception as e:
        return make_error("The supplied DOMLX model is malformed or its DOML version is unsupported.", debug_msg=str(e)), 400

def csp_html(body, version=None):
    ret = csp(body, version)
    return render_template('csp.html.jinja', **ret).replace('\n', '')
