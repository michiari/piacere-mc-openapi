import importlib.resources as ilres
import yaml
from joblib import parallel_backend, Parallel, delayed
from z3 import CheckSatResult, sat, unsat, unknown

from .. import assets
from .intermediate_model.doml_element import (
    IntermediateModel,
    reciprocate_inverse_associations
)
from .intermediate_model.metamodel import (
    parse_inverse_associations,
    parse_metamodel
)
from .xmi_parser.doml_model import parse_doml_model
from .imc import RequirementStore, IntermediateModelChecker
from .common_reqs import CommonRequirements


class ModelChecker:
    metamodel = None
    inv_assoc = None

    @staticmethod
    def init_metamodel():
        mmdoc = yaml.load(ilres.read_text(assets, "doml_meta.yaml"), yaml.Loader)
        ModelChecker.metamodel = parse_metamodel(mmdoc)
        ModelChecker.inv_assoc = parse_inverse_associations(mmdoc)

    def __init__(self, xmi_model: bytes):
        assert ModelChecker.metamodel and ModelChecker.inv_assoc
        self.intermediate_model: IntermediateModel = parse_doml_model(xmi_model, ModelChecker.metamodel)
        reciprocate_inverse_associations(self.intermediate_model, ModelChecker.inv_assoc)

    def check_common_requirements(self, threads=1) -> tuple[CheckSatResult, str]:
        def worker(index: int):
            imc = IntermediateModelChecker(ModelChecker.metamodel, ModelChecker.inv_assoc, self.intermediate_model)
            if index >= 0:
                rs = RequirementStore([CommonRequirements.get_one_requirement(index)])
                return imc.check_requirements(rs)
            else:
                return imc.check_consistency_constraints()

        if threads <= 1:
            imc = IntermediateModelChecker(ModelChecker.metamodel, ModelChecker.inv_assoc, self.intermediate_model)
            cons = imc.check_consistency_constraints()
            reqs = imc.check_requirements(CommonRequirements)
            results = [cons, reqs]
        else:
            with parallel_backend('threading', n_jobs=threads):
                results = Parallel()(delayed(worker)(i) for i in range(-1, CommonRequirements.get_num_requirements()))

        some_unsat = any(res == unsat for res, _ in results)
        some_dontknow = any(res == unknown for res, _ in results)

        if some_unsat:
            err_msg = " ".join(msg for res, msg in results if res == unsat)
            if some_dontknow:
                err_msg = err_msg + "Unable to check some requirements."
            return unsat, err_msg
        elif some_dontknow:
            return unknown, "Unable to check some requirements."
        else:
            return sat, "All requirements satisfied."
