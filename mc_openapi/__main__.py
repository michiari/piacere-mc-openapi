#!/usr/bin/env python3
import argparse

from mc_openapi.app_config import app
from mc_openapi.doml_mc import DOMLVersion
from mc_openapi.doml_mc.domlr_parser.exceptions import RequirementException
from mc_openapi.doml_mc.domlr_parser.parser import DOMLRTransformer, Parser, SynthesisDOMLRTransformer
from mc_openapi.doml_mc.imc import RequirementStore
from mc_openapi.doml_mc.intermediate_model.metamodel import MetaModelDocs
from mc_openapi.doml_mc.mc import ModelChecker
from mc_openapi.doml_mc.mc_result import MCResult

parser = argparse.ArgumentParser()

parser.add_argument("-d", "--doml", dest="doml", help="the DOMLX file to check")
parser.add_argument("-V", "--doml-version", dest="doml_version", default="V2_0", help="(optional) the version used by the DOMLX file")
parser.add_argument("-r", "--requirements", dest="requirements", help="the user-specified requirements file to check")
parser.add_argument("-p", "--port", dest="port", type=int, default=8080, help="the port exposing the model checker REST API (default: 8080)")
parser.add_argument("-v", "--verbose", dest="verbose", action='store_true', help="print a detailed human-readable output of everything going on. Helpful for debugging.")
# Model Checker
parser.add_argument("-c", "--check-consistency", dest="consistency", action='store_true', help="check on additional built-in consistency requirements")
parser.add_argument("-S", "--skip-common-checks", dest="skip_common", action='store_true', help="skip check on common built-in requirements")
parser.add_argument("-t", "--threads", dest="threads", type=int, default=2, help="number of threads used by the model checker")
# Synthesis
parser.add_argument("-s", "--synth", dest="synth", action='store_true', help="synthetize a new DOMLX file from requirements")
parser.add_argument("-m", "--max-tries", dest="tries", type=int, default=10, help="max number of iteration while trying to solve the model with unbounded variables")

args = parser.parse_args()

# Print only when -v flag is true
def printv(*_args):
    if args.verbose:
        print(*_args)

printv("== Verbose: ON ==")

if not args.doml and not args.synth:
    # Start the webserver
    app.run(port=args.port)
else:
    # Run only it via command line
    doml_path = args.doml
    reqs_path = args.requirements

    # Try using the user-provided DOML version
    try:
        doml_ver = DOMLVersion[args.doml_version]
    except:
        # Suggest valid DOML versions
        print(f"Unknown DOML version '{args.doml_version}'")
        versions = [ ver.name for ver in list(DOMLVersion)]
        print(f"Available DOML versions = {versions}")
        exit(1)

    with open(doml_path, "rb") as xmif:
        # Read DOML file from path
        doml_xmi = xmif.read()

    # Config the model checker (setup metamodels and intermediate models)
    dmc = ModelChecker(doml_xmi, doml_ver)

    user_req_store = RequirementStore()
    user_req_str_consts = []

    if reqs_path:
        with open(reqs_path, "r") as reqsf:
        # Read the user requirements written in DSL
            user_reqs = reqsf.read()
        # Parse them
        try:
            domlr_parser = Parser(DOMLRTransformer)
            user_req_store, user_req_str_consts = domlr_parser.parse(user_reqs)
        except Exception as e:
            print(e)
            raise RuntimeError("Failed to parse the DOMLR.")

    if not args.synth:
        try:
            # Check satisfiability
            results = dmc.check_requirements(
                threads=args.threads, 
                user_requirements=user_req_store,
                user_str_values=user_req_str_consts,
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

    else: # Synthesis
        printv("Running synthesis...")
        # Lazy load libraries
        from doml_synthesis.types import State
        from doml_synthesis.data import init_data
        from doml_synthesis.solver import solve
        from doml_synthesis.requirements import builtin_requirements
        from doml_synthesis.results import check_synth_results, save_results

        # Required files:
        mm = MetaModelDocs[doml_ver]
        im = {
            k: { 
                'id': v.id_,
                'name': v.user_friendly_name,
                'class': v.class_,
                'assocs': v.associations,
                'attrs': v.attributes
            }
            for k, v in  dmc.intermediate_model.items()
        }

        # Parse
        synth_domlr_parser = Parser(SynthesisDOMLRTransformer)
        synth_user_reqs, user_reqs_strings = synth_domlr_parser.parse(user_reqs)

        print(user_reqs_strings)
        
        state = State()
        # Parse MM and IM
        state = init_data(state, doml=im, metamodel=mm)
        # Solve

        state = solve(
            state, 
            requirements=[builtin_requirements, synth_user_reqs], 
            strings=user_reqs_strings, 
            max_tries=args.tries
        )
        # Update state
        state = save_results(state)
        # Print output
        state = check_synth_results(state)