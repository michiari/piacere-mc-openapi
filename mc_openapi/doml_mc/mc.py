import importlib.resources as ilres
import yaml
from joblib import parallel_backend, Parallel, delayed

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
from .mc_result import MCResults
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

    def check_common_requirements(self, threads=1) -> MCResults:
        def worker(index: int):
            imc = IntermediateModelChecker(ModelChecker.metamodel, ModelChecker.inv_assoc, self.intermediate_model)
            if index >= 0:
                rs = RequirementStore([CommonRequirements.get_one_requirement(index)])
                return imc.check_requirements(rs)
            else:
                return MCResults([imc.check_consistency_constraints()])

        if threads <= 1:
            imc = IntermediateModelChecker(ModelChecker.metamodel, ModelChecker.inv_assoc, self.intermediate_model)
            cons = imc.check_consistency_constraints()
            reqs = imc.check_requirements(CommonRequirements)
            return reqs.add_result(cons)
        else:
            with parallel_backend('threading', n_jobs=threads):
                results = Parallel()(delayed(worker)(i) for i in range(-1, CommonRequirements.get_num_requirements()))
            ret = MCResults([])
            for res in results:
                ret.add_results(res)
            return ret
