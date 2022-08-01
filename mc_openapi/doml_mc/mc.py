from typing import Optional
import importlib.resources as ilres
import yaml
from joblib import parallel_backend, Parallel, delayed

from .. import assets
from .intermediate_model.doml_element import (
    IntermediateModel,
    reciprocate_inverse_associations
)
from .intermediate_model.metamodel import (
    MetaModel,
    parse_inverse_associations,
    parse_metamodel
)
from .xmi_parser.doml_model import parse_doml_model
from .mc_result import MCResults
from .imc import RequirementStore, IntermediateModelChecker
from .common_reqs import CommonRequirements
from .consistency_reqs import (
    get_attribute_type_reqs,
    get_attribute_multiplicity_reqs,
    get_association_type_reqs,
    get_association_multiplicity_reqs,
    get_inverse_association_reqs
)


class ModelChecker:
    metamodel: Optional[MetaModel] = None
    inv_assoc: Optional[list[tuple[str, str]]] = None

    @staticmethod
    def init_metamodel():
        mmdoc = yaml.load(ilres.read_text(assets, "doml_meta.yaml"), yaml.Loader)
        ModelChecker.metamodel = parse_metamodel(mmdoc)
        ModelChecker.inv_assoc = parse_inverse_associations(mmdoc)

    def __init__(self, xmi_model: bytes):
        assert ModelChecker.metamodel and ModelChecker.inv_assoc
        self.intermediate_model: IntermediateModel = parse_doml_model(xmi_model, ModelChecker.metamodel)
        reciprocate_inverse_associations(self.intermediate_model, ModelChecker.inv_assoc)

    def check_common_requirements(self, threads=1, consistency_checks=False) -> MCResults:
        assert ModelChecker.metamodel and ModelChecker.inv_assoc
        req_store = CommonRequirements
        if consistency_checks:
            req_store = req_store \
                + get_attribute_type_reqs(ModelChecker.metamodel) \
                + get_attribute_multiplicity_reqs(ModelChecker.metamodel) \
                + get_association_type_reqs(ModelChecker.metamodel) \
                + get_association_multiplicity_reqs(ModelChecker.metamodel) \
                + get_inverse_association_reqs(ModelChecker.inv_assoc)

        def worker(index: int):
            imc = IntermediateModelChecker(ModelChecker.metamodel, ModelChecker.inv_assoc, self.intermediate_model)
            rs = RequirementStore([req_store.get_one_requirement(index)])
            return imc.check_requirements(rs)

        if threads <= 1:
            imc = IntermediateModelChecker(ModelChecker.metamodel, ModelChecker.inv_assoc, self.intermediate_model)
            reqs = imc.check_requirements(req_store)
            return reqs
        else:
            with parallel_backend('threading', n_jobs=threads):
                results = Parallel()(delayed(worker)(i) for i in range(len(req_store)))
            ret = MCResults([])
            for res in results:
                ret.add_results(res)
            return ret
