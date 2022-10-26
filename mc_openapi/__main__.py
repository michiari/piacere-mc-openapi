#!/usr/bin/env python3
import argparse

from mc_openapi.app_config import app
from mc_openapi.doml_mc import DOMLVersion
from mc_openapi.doml_mc.dsl_parser.exceptions import RequirementException
from mc_openapi.doml_mc.mc import ModelChecker
from mc_openapi.doml_mc.mc_result import MCResult

parser = argparse.ArgumentParser()

parser.add_argument("-d", "--doml", dest="doml", help="the DOMLX file to check")
parser.add_argument("-V", "--doml-version", dest="doml_version", default="V2_0", help="(optional) the version used by the DOMLX file")
parser.add_argument("-r", "--requirements", dest="requirements", help="the user-specified requirements file to check")
parser.add_argument("-c", "--check-consistency", dest="consistency", action='store_true', help="check on additional built-in consistency requirements")
parser.add_argument("-S", "--skip-common-checks", dest="skip_common", action='store_true', help="skip check on common built-in requirements")
parser.add_argument("-t", "--threads", dest="threads", type=int, default=2, help="number of threads used by the model checker")

args = parser.parse_args()

if not args.doml:
    # Start the webserver
    app.run(port=8080)
else:
    # Run only it via command line
    doml_path = args.doml
    reqs_path = args.requirements
    try:
        doml_ver = DOMLVersion[args.doml_version]
    except:
        print(f"Unknown DOML version '{args.doml_version}'")
        versions = [ ver.name for ver in list(DOMLVersion)]
        print(f"Available DOML versions = {versions}")
        exit(1)

    with open(doml_path, "rb") as xmif:
        # Read DOML file from path
        doml_xmi = xmif.read()

        # Config the model checker
        dmc = ModelChecker(doml_xmi, doml_ver)

        user_reqs = None
        if reqs_path:
            with open(reqs_path, "r") as reqsf:
            # Read the user requirements written in DSL
                user_reqs = reqsf.read()

        try:
            # Check satisfiability
            results = dmc.check_requirements(
                threads=args.threads, 
                user_requirements=user_reqs, 
                consistency_checks=args.consistency,
                skip_common_requirements=args.skip_common
            )

            res, msg = results.summarize()

            if res == MCResult.sat:
                print("sat")
            else:
                print(res.name)
                print("\033[91m{}\033[00m".format(msg))
        except RequirementException as e:
            print(e.message)