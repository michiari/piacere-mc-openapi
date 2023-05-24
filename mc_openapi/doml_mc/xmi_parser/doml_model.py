import copy
import importlib.resources as ilres
import logging
import sys
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
                    raise RuntimeError(f"DOML model is using an unsupported version: {v_str}")
        else:
            return DOMLVersion.V2_0  # Should be DOMLVersion.V1_0, but we use V2_0 because the 2.1 IDE doesn't fill it
    else:
        raise RuntimeError(f"The DOML version is unsupported or the model is malformed.\nLowest supported version is: {DOMLVersion.V2_0}")


def parse_doml_model(raw_model: bytes, doml_version: Optional[DOMLVersion]) -> Tuple[IntermediateModel, DOMLVersion]:    
    # if doml_version is None:
    #     doml_version = infer_domlx_version(raw_model)

    # Try every DOML version until one works!
    if doml_version is None:

        doml_versions = [x for x in DOMLVersion]
        # Use the most recent DOML version first
        doml_versions.reverse() 

        def get_model(raw_model, doml_version):
            try:
                dv = doml_versions.pop(0)
                doml_version = dv
                parsed_xmi_model = parse_xmi_model(raw_model, dv)
                # Try to extract the user-specified version from the DOML
                try:
                    model_version = parsed_xmi_model.version
                    if model_version:
                        try:
                            dv = DOMLVersion.get(model_version)
                            return parse_xmi_model(raw_model, dv), dv
                        except:
                            MSG_ERR_INVALID_DOML_VERSION = f"DOML requires version \"{model_version}\", but could not parse it with that version. Is the version valid?"
                            logging.error(MSG_ERR_INVALID_DOML_VERSION)
                            raise RuntimeError(MSG_ERR_INVALID_DOML_VERSION)
                except:
                    pass
                # DOML version is not specified, proceed as usual 
                return parsed_xmi_model, dv
            except Exception as e:
                logging.info(f"Couldn't parse with DOML {dv.value}. Trying another version...")
                if len(doml_versions) == 0:
                    MSG_ERR_NO_DOML_VERSIONS = "No other compatible DOML versions found!"
                    logging.error(MSG_ERR_NO_DOML_VERSIONS)
                    raise RuntimeError(MSG_ERR_NO_DOML_VERSIONS)
                else:
                    return get_model(raw_model, doml_version)

        model, doml_version = get_model(raw_model, doml_version)
    else: # if user specifies DOML version, respect that choice!
        try:
            model = parse_xmi_model(raw_model, doml_version)
        except:
            raise RuntimeError("Parsing of DOML failed. Perhaps you are using the wrong DOML version or IDE?")

    logging.info(f"Model '{model.name}' parsed as DOML {doml_version.value}")

    elp = ELayerParser(MetaModels[doml_version], SpecialParsers[doml_version])
    if model.application:
        elp.parse_elayer(model.application)
    if model.infrastructure:
        elp.parse_elayer(model.infrastructure)
    else:
        raise RuntimeError("Abstract infrastructure layer is missing from DOML.")
    if model.activeConfiguration:
        elp.parse_elayer(model.activeConfiguration)
    if model.activeInfrastructure:
        im = elp.parse_elayer(model.activeInfrastructure)
    else:
        raise RuntimeError("No active concrete infrastructure layer has been specified in DOML.")

    reciprocate_inverse_associations(im, InverseAssociations[doml_version])

    return im, doml_version

def get_pyecore_model(raw_model: bytes, doml_version: Optional[DOMLVersion]) -> EObject:
    if doml_version is None:
        doml_version = infer_domlx_version(raw_model)
    # TODO: See if its better replaced by the get_model() in parse_doml_version() 
    return parse_xmi_model(raw_model, doml_version)
