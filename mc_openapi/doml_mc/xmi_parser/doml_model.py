import copy
import importlib.resources as ilres
from typing import Optional, Tuple

from lxml import etree
from pyecore.ecore import EObject
from pyecore.resources import ResourceSet

from mc_openapi import assets

from ..intermediate_model.doml_element import (
    IntermediateModel, reciprocate_inverse_associations)
from ..intermediate_model.metamodel import (DOMLVersion, InverseAssociations,
                                            MetaModels)
from .bytes_uri import BytesURI
from .ecore import ELayerParser
from .special_parsers import SpecialParsers

doml_rsets = {}
def init_doml_rsets():  # noqa: E302
    global doml_rsets
    for ver in DOMLVersion:
        rset = ResourceSet()
        source = ilres.files(assets).joinpath(f"doml_{ver.value}.ecore")
        resource = rset.get_resource(BytesURI(
            "doml", bytes=source.read_bytes()
        ))
        doml_metamodel = resource.contents[0]

        rset.metamodel_registry[doml_metamodel.nsURI] = doml_metamodel
        # .ecore file is loaded in the rset as a metamodel
        for subp in doml_metamodel.eSubpackages:
            rset.metamodel_registry[subp.nsURI] = subp

        doml_rsets[ver] = rset


def get_rset(doml_version: DOMLVersion) -> ResourceSet:
    return copy.copy(doml_rsets[doml_version])


def parse_xmi_model(raw_model: bytes, doml_version: DOMLVersion) -> EObject:
    rset = get_rset(doml_version)
    doml_uri = BytesURI("user_doml", bytes=raw_model)
    resource = rset.create_resource(doml_uri)
    resource.load()
    return resource.contents[0]


def infer_domlx_version(raw_model: bytes) -> DOMLVersion:
    root = etree.fromstring(raw_model)
    if root.tag == "{http://www.piacere-project.eu/doml/commons}DOMLModel":
        if "version" in root.attrib:
            v_str = root.attrib["version"]
            try:
                return DOMLVersion(v_str)
            except ValueError:
                if v_str == "v2":
                    return DOMLVersion.V2_0
                else:
                    raise RuntimeError(f"Supplied with DOMLX model of unsupported version {v_str}")
        else:
            return DOMLVersion.V2_0  # Should be DOMLVersion.V1_0, but we use V2_0 because the 2.1 IDE doesn't fill it
    else:
        raise RuntimeError(f"Supplied with malformed DOMLX model or unsupported DOML version.\nIn use version is: {DOMLVersion.V2_0}")


def parse_doml_model(raw_model: bytes, doml_version: Optional[DOMLVersion]) -> Tuple[IntermediateModel, DOMLVersion]:
    if doml_version is None:
        doml_version = infer_domlx_version(raw_model)

    model = parse_xmi_model(raw_model, doml_version)

    elp = ELayerParser(MetaModels[doml_version], SpecialParsers[doml_version])
    if model.application:
        elp.parse_elayer(model.application)
    if model.infrastructure:
        elp.parse_elayer(model.infrastructure)
    else:
        raise RuntimeError("Abstract infrastructure layer is missing.")
    if model.activeConfiguration:
        elp.parse_elayer(model.activeConfiguration)
    if model.activeInfrastructure:
        im = elp.parse_elayer(model.activeInfrastructure)
    else:
        raise RuntimeError("No active concrete infrastructure layer has been specified.")

    reciprocate_inverse_associations(im, InverseAssociations[doml_version])

    return im, doml_version

def get_pyecore_model(raw_model: bytes, doml_version: Optional[DOMLVersion]) -> EObject:
    if doml_version is None:
        doml_version = infer_domlx_version(raw_model)

    return parse_xmi_model(raw_model, doml_version)

from typing import Optional

def serialize_pyecore_model(root: EObject, doml_version: DOMLVersion = DOMLVersion.V2_0, path: Optional[str] = None):
    from pyecore.resources import URI

    # Get rset with metamodel
    rset = get_rset(doml_version) 
    # Create the resource where we'll save the updated model/DOMLX
    res = rset.create_resource(URI("./output.domlx"))
    # Append updated EObject
    res.append(root)
    # Serialize to file
    res.save()
