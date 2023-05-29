#!/usr/bin/env python3
import argparse
import logging
from logging.config import dictConfig
import re

from tabulate import tabulate

from mc_openapi.app_config import app
from mc_openapi.doml_mc import DOMLVersion, init_model, verify_csp_compatibility, verify_model, synthesize_model
from mc_openapi.doml_mc.domlr_parser.exceptions import RequirementException
from mc_openapi.doml_mc.mc_result import MCResult

from . import __version__

parser = argparse.ArgumentParser()

parser.add_argument("-d", "--doml", dest="doml", help="the DOMLX file to check")
parser.add_argument("-V", "--doml-version", dest="doml_version", help="(optional) the version used by the DOMLX file")
parser.add_argument("-r", "--requirements", dest="requirements", help="the user-specified requirements file to check")
parser.add_argument("-p", "--port", dest="port", type=int, default=8080, help="the port exposing the model checker REST API (default: 8080)")
parser.add_argument("-v", "--verbose", dest="verbose", action='store_true', help="print a detailed human-readable output of everything going on. Helpful for debugging.")
# Model Checker
parser.add_argument("-c", "--check-consistency", dest="consistency", action='store_true', help="check on additional built-in consistency requirements")
parser.add_argument("-S", "--skip-builtin-checks", dest="skip_builtin", action='store_true', help="skip check on built-in requirements")
parser.add_argument("-C", "--csp", dest="csp", action='store_true', help="check compatibility with supported CSPs")
parser.add_argument("-t", "--threads", dest="threads", type=int, default=2, help="number of threads used by the model checker")

# Synthesis
parser.add_argument("-s", "--synth", dest="synth", action='store_true', help="synthetize a new DOMLX file from requirements")
parser.add_argument("-m", "--max-tries", dest="tries", type=int, default=8, help="max number of iteration while trying to solve the model with unbounded variables")

args = parser.parse_args()

if not args.doml and not args.synth:
    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] %(levelname)s: %(message)s',
        }},
        'handlers': {'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        }},
        'root': {
            'level': 'DEBUG',
            'handlers': ['wsgi']
        }
    })
    logging.info(f"DOML Model Checker v{__version__}")

    # Start the webserver
    app.run(port=args.port)
else:
    logging.basicConfig(level=logging.DEBUG, format='* %(message)s')
    logging.info(f"DOML Model Checker v{__version__}")

    doml_path = args.doml
    domlr_path = args.requirements

    # Validate user-provided DOML version
    doml_ver = None
    if args.doml_version is not None:
        try:
            doml_ver = DOMLVersion.get(args.doml_version)
        except:
            # Suggest valid DOML versions
            print(f"Unknown DOML version '{args.doml_version}'")
            versions = [ ver.name for ver in list(DOMLVersion)]
            print(f"Available DOML versions = {versions}")
            exit(1)

    # Read DOMLX from path
    with open(doml_path, "rb") as xmif:
        # Read DOML file from path
        doml_xmi = xmif.read()

    # Read DOMLR from path
    domlr_src = None
    if domlr_path:
        with open(domlr_path, "r") as domlr_file:
        # Read the user requirements written in DSL
            domlr_src = domlr_file.read()

    # Config the model checker
    dmc = init_model(doml_xmi, doml_ver)

    ####### END OF INIT STEP #######
    if not args.synth: # Verify Model/CSP Compatibility

        # Check CSP Compatibility
        if args.csp:
            csp = verify_csp_compatibility(dmc)
            for csp_k, csp_v in csp.items():
                # Format items in minreq
                if csp_k == 'minreq':
                    for row in csp_v:
                        for index, col in enumerate(row):
                            if index > 0 and isinstance(col, list):
                                row[index] = "\n".join(col)

                print(tabulate(csp_v, headers='firstrow', tablefmt='fancy_grid'))
        else:
            result, msg = verify_model(dmc, domlr_src, args.threads, args.consistency, args.skip_builtin)

            print("[RESULT]")
            if result == MCResult.sat:
                print("sat")
            else:
                print(result.name)
                print("[ERRORS]")
                print("\033[91m{}\033[00m".format(msg))


    else: # Synthesis
        synthesize_model(dmc, domlr_src, args.tries)
        # TODO: Do something with the results
        