import logging
from typing import Optional

import doml_synthesis as DOMLS
from doml_synthesis import State, builtin_requirements

from mc_openapi.doml_mc import ModelChecker
from mc_openapi.doml_mc.common_reqs import CommonRequirements
from mc_openapi.doml_mc.consistency_reqs import get_association_multiplicity_reqs, get_association_type_reqs, get_attribute_multiplicity_reqs, get_attribute_type_reqs, get_inverse_association_reqs
from mc_openapi.doml_mc.csp_compatibility import \
    CSPCompatibilityValidator as CSPCompatibility
from mc_openapi.doml_mc.domlr_parser import (DOMLRTransformer, Parser,
                                             SynthesisDOMLRTransformer)
from mc_openapi.doml_mc.imc import RequirementStore
from mc_openapi.doml_mc.intermediate_model.metamodel import (DOMLVersion,
                                                             MetaModelDocs)


def init_model(domlx:bytes, doml_ver: DOMLVersion):
    dmc = ModelChecker(domlx, doml_ver)
    logging.info("Parsed DOMLX successfully.")
    return dmc


def verify_model(
        dmc: ModelChecker,
        external_domlr: Optional[str] = None,
        threads: int = 2,
        consistency_checks: bool = False, 
        skip_builtin_checks: bool = False
    ):
    # DOMLR parser
    domlr_parser = Parser(DOMLRTransformer)

    # General req store
    req_store = RequirementStore()

    # Store of Requirements and unique string constants
    user_req_store, user_req_str_consts = RequirementStore(), []

    flags = {}

    # Parse external DOMLR file
    if external_domlr:
        user_req_store, user_req_str_consts = domlr_parser.parse(external_domlr)

    # Parse internal DOMLR requirements
    if DOMLVersion.has_DOMLR_support(dmc.doml_version):
        func_reqs = dmc.domlr_requirements
        for _, req_text in func_reqs:
            doml_req_store, doml_req_str_consts, doml_req_flags = domlr_parser.parse(req_text)
            user_req_store += doml_req_store
            user_req_str_consts += doml_req_str_consts
            flags |= doml_req_flags

    # Remove duplicate tokens   
    user_req_str_consts = list(set(user_req_str_consts))

    # Built-in requirements
    if not (flags.get('_ignore_builtin', False) or skip_builtin_checks):
        req_store += CommonRequirements[dmc.doml_version]
        # Skip selected requirements
        req_store.skip_requirements_by_id([k for k,v in flags.items() if not k.startswith("_") and v is False])

    # Consistency requirements (disabled by default)
    if flags.get('_check_consistency', False) or consistency_checks:
        logging.warning("Consistency checks are outdated and may break at any time.")
        req_store = req_store \
            + get_attribute_type_reqs(dmc.metamodel) \
            + get_attribute_multiplicity_reqs(dmc.metamodel) \
            + get_association_type_reqs(dmc.metamodel) \
            + get_association_multiplicity_reqs(dmc.metamodel) \
            + get_inverse_association_reqs(dmc.inv_assoc)

    # Add user requirements at the end
    req_store += user_req_store

    # Log all requirements to check
    logging.debug("Checking following requirements: " + ", ".join([k.assert_name for k in req_store.get_all_requirements()]))

    # Check CSP
    if flags.get('_csp', False):
        logging.warning("The CSP compatibility check is not yet implemented via DOMLR")

    # Check satisfiability
    results = dmc.check_requirements(
        req_store,
        threads=threads, 
        user_str_values=user_req_str_consts,
        disable_multithreading=(threads == 1)
    )

    res = results.summarize()

    res['doml_version'] = dmc.doml_version.name

    logging.info(res)

    return res

def synthesize_model(dmc: ModelChecker, external_domlr: str, max_tries: int):
    logging.warn("Synthesis is experimental and might not be up-to-date with the latest DOML.")

    synth_domlr_parser = Parser(SynthesisDOMLRTransformer)
    mm = MetaModelDocs[dmc.doml_version]
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

    user_req_store, user_req_str_consts = [], []


    if external_domlr:
        user_req_store, user_req_str_consts = synth_domlr_parser.parse(external_domlr, for_synthesis=True)


    # Parse internal DOMLR requirements
    if DOMLVersion.has_DOMLR_support(dmc.doml_version):
        func_reqs = dmc.domlr_requirements
        for _, req_text in func_reqs:
            doml_req_store, doml_req_str_consts, doml_req_flags = synth_domlr_parser.parse(req_text, for_synthesis=True)
            user_req_store += doml_req_store
            user_req_str_consts += doml_req_str_consts
            flags |= doml_req_flags
    
    # Remove duplicated strings
    user_req_str_consts = list(set(user_req_str_consts))

    state = State()
    # Parse MM and IM
    state = DOMLS.init_data(
        state, 
        doml=im, 
        metamodel=mm, 
    )

    reqs = user_req_store

    reqs += builtin_requirements

    state = DOMLS.solve(
        state, 
        requirements=reqs, 
        strings=user_req_str_consts,
        max_tries=max_tries
    )
    # Update state
    state = DOMLS.save_results(state)
    # Print output
    state = DOMLS.check_synth_results(state)

    
def verify_csp_compatibility(dmc: ModelChecker):
    return CSPCompatibility.check(dmc.intermediate_model, dmc.doml_version)
    