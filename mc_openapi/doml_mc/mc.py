from multiprocessing import TimeoutError
from typing import Optional

from joblib import Parallel, delayed, parallel_backend

from .common_reqs import CommonRequirements
from .consistency_reqs import (get_association_multiplicity_reqs,
                               get_association_type_reqs,
                               get_attribute_multiplicity_reqs,
                               get_attribute_type_reqs,
                               get_inverse_association_reqs)
from .imc import IntermediateModelChecker, RequirementStore
from .intermediate_model.metamodel import (DOMLVersion, InverseAssociations,
                                           MetaModels)
from .mc_result import MCResult, MCResults
from .xmi_parser.doml_model import parse_doml_model


class ModelChecker:
    def __init__(self, xmi_model: bytes, doml_version: Optional[DOMLVersion] = None):
        self.intermediate_model, self.doml_version = parse_doml_model(
            xmi_model, doml_version)
        self.metamodel = MetaModels[self.doml_version]
        self.inv_assoc = InverseAssociations[self.doml_version]

    def check_requirements(
        self,
        threads: int = 1,
        user_requirements: Optional[RequirementStore] = None,
        user_str_values: list[str] = [],
        skip_common_requirements: bool = False,
        consistency_checks: bool = False,
        timeout: Optional[int] = None
    ) -> MCResults:
        assert self.metamodel and self.inv_assoc
        req_store = RequirementStore([])

        if not skip_common_requirements:
            req_store += CommonRequirements[self.doml_version]

        if consistency_checks:
            req_store = req_store \
                + get_attribute_type_reqs(self.metamodel) \
                + get_attribute_multiplicity_reqs(self.metamodel) \
                + get_association_type_reqs(self.metamodel) \
                + get_association_multiplicity_reqs(self.metamodel) \
                + get_inverse_association_reqs(self.inv_assoc)

        if user_requirements:
            req_store += user_requirements

        def worker(rfrom: int, rto: int):
            imc = IntermediateModelChecker(
                self.metamodel, self.inv_assoc, self.intermediate_model)
            rs = RequirementStore(req_store.get_all_requirements()[rfrom:rto])
            imc.instantiate_solver(user_str_values)
            return imc.check_requirements(rs)

        def split_reqs(n_reqs: int, n_split: int):
            slice_size = max(n_reqs // n_split, 1)

            rto = 0
            while rto < n_reqs:
                rfrom = rto
                rto = min(rfrom + slice_size, n_reqs)
                yield rfrom, rto

        try:
            with parallel_backend('loky', n_jobs=threads):
                results = Parallel(timeout=timeout)(delayed(worker)(
                    rfrom, rto) for rfrom, rto in split_reqs(len(req_store), threads))

            # Uncomment for ease of debug
            # results =[ worker(0, len(req_store) )]

            ret = MCResults([])
            for res in results:
                ret.add_results(res)

            return ret
        except TimeoutError:
            return MCResults([(MCResult.dontknow, "")])
