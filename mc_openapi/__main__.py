#!/usr/bin/env python3
import argparse

from mc_openapi.app_config import app
from mc_openapi.doml_mc import DOMLVersion
from mc_openapi.doml_mc.dsl_parser.exceptions import RequirementException
from mc_openapi.doml_mc.dsl_parser.parser import Parser
from mc_openapi.doml_mc.imc import RequirementStore
from mc_openapi.doml_mc.mc import ModelChecker
from mc_openapi.doml_mc.mc_result import MCResult
from mc_openapi.doml_mc.synthesis.synthesis import Synthesis
from mc_openapi.doml_mc.synthesis.synthesis_common_reqs import synthesis_default_req_store

parser = argparse.ArgumentParser()

parser.add_argument("-d", "--doml", dest="doml", help="the DOMLX file to check")
parser.add_argument("-V", "--doml-version", dest="doml_version", default="V2_0", help="(optional) the version used by the DOMLX file")
parser.add_argument("-r", "--requirements", dest="requirements", help="the user-specified requirements file to check")
# Model Checker
parser.add_argument("-c", "--check-consistency", dest="consistency", action='store_true', help="check on additional built-in consistency requirements")
parser.add_argument("-S", "--skip-common-checks", dest="skip_common", action='store_true', help="skip check on common built-in requirements")
parser.add_argument("-t", "--threads", dest="threads", type=int, default=2, help="number of threads used by the model checker")
# Synthesis
parser.add_argument("-s", "--synth", dest="synth", action='store_true', help="synthetize a new DOMLX file from requirements")
parser.add_argument("-m", "--max-tries", dest="tries", type=int, default=10, help="max number of iteration while trying to solve the model with unbounded variables")

args = parser.parse_args()

if not args.doml and not args.synth:
    # Start the webserver
    app.run(port=8080)
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
            domlr_parser = Parser()
            user_req_store, user_req_str_consts = domlr_parser.parse(user_reqs)
        except Exception as e:
            print(e)
            raise RuntimeError("Failed to parse the DOMLR.")

    if args.synth:
        

        # try:
            synth = Synthesis(dmc.metamodel, dmc.intermediate_model, doml_ver)

            synth_req_store = RequirementStore()

            synth_req_store += synthesis_default_req_store
            synth_req_store += user_req_store

            print(f"synth_reqs : {len(synth_req_store)}")

            solved_ctx = synth.check(
                ub_elems_n=0,
                ub_vals_n=0,
                max_tries=args.tries, # default = 10
                reqs=synth_req_store.get_all_requirements(), 
                user_req_strings=user_req_str_consts)
            solved_model = solved_ctx.solver.model()

            # Print new found relationships
            ub_elems_and_assoc = synth.get_ub_elems_and_assoc(solved_ctx, solved_model)
            print("\n".join([synth.pretty_ub_elems_assoc(assoc) for assoc in ub_elems_and_assoc]))
            print("-" * 120)
            ub_vals_and_attr = synth.get_ub_vals_and_attr(solved_ctx, solved_model)
            print("\n".join([synth.pretty_ub_vals_attr(attr) for attr in ub_vals_and_attr]))

            # find thinned results
            assoc_to_implement = synth.thin_ub_elems_and_assoc(solved_ctx, ub_elems_and_assoc)
            attrs_to_implement = synth.thin_ub_vals_and_attr(solved_ctx, ub_vals_and_attr)

            # Print results
            print("\nPlease implement the following:\n")
            print("\n".join([synth.pretty_ub_elems_assoc(assoc) for assoc in assoc_to_implement]))
            print("\n".join([synth.pretty_ub_vals_attr(attr) for attr in attrs_to_implement]))

            
        # except Exception as e:
        #     print(e)

    else:
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