import re
from itertools import product

from pyecore.ecore import EClass, EObject

from mc_openapi.doml_mc.intermediate_model.doml_element import \
    IntermediateModel
from mc_openapi.doml_mc.intermediate_model.metamodel import DOMLVersion
from mc_openapi.doml_mc.synthesis.synthesis import AssocAndElems
from mc_openapi.doml_mc.xmi_parser.doml_model import get_rset

import secrets
import base64

def _gen_random_suffix_hash(len: int = 6):
    return base64.urlsafe_b64encode(secrets.token_bytes(len)).decode()

def _convert_camelcase_to_snakecase(input: str):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', input).lower()

def generate_xmi(root: EObject, new_assocs: list[AssocAndElems], im: IntermediateModel, doml_ver: DOMLVersion = DOMLVersion.V2_0):

    def find_eclass(eclass_package: str, eclass_name: str):
        """`eclass_package` is like `infrastructure`
           `eclass_name` is like `VirtualMachine`
        """
        pkgs = [pkg for pkg 
            in list(get_rset(doml_ver).metamodel_registry.values()) 
            if pkg.name == eclass_package
        ]
        # `metamodel_registry` is a dict consisting of:
        # - ecore
        # - doml
        # |- commons
        # |- application
        # |- infrastructure
        # |- concrete
        # |- optimization
        return pkgs[0].getEClassifier(eclass_name)

    def find_elem(elem_name: str):
        ret = []
        for elem in root.eAllContents():
            try:
                if elem.name == elem_name:
                    ret.append(elem)
            except:
                pass
        return ret[0]

    print(find_eclass("infrastructure", "NetworkInterface"))

    for ((e1_k, e1_v), assoc, (e2_k, e2_v)) in new_assocs:
        if "unbound" not in e1_k:
            # it's an existing element
            e1 = im[e1_k]
            e1_class = re.search("^.*_(.+?)$", e1.class_).group(1)
            e1_name = e1.attributes["commons_DOMLElement::name"][0]
            print(e1_class, e1_name)
        # TODO: Should I handle the case where the first element is an unbound one?

        e1_instance = find_elem(e1_name)

        # Regex to split <package>_<class>::<name>
        assoc_re = re.search("^(.+?)_(.+?)::(.+?)$", str(assoc))
        assoc_package = assoc_re.group(1)
        assoc_class = assoc_re.group(2)
        assoc_name = assoc_re.group(3)
        print(assoc_package, assoc_class, assoc_name)

        if "unbound" not in e2_k:
            # it's an existing element
            e2 = im[e2_k]
            e2_class = re.search("^.*_(.+?)$", e2.class_).group(1)
            e2_name = e2.attributes["commons_DOMLElement::name"][0]
            print(e2_class, e2_name)
            # TODO: Add relationship between the two?
        else:
            e1_container = getattr(e1_instance, assoc_name)
            e2_instance_type = e1_container.feature.eType
            e2_instance_name = (
                _convert_camelcase_to_snakecase(e1_container.feature.eType.name)
                + "_" 
                + _gen_random_suffix_hash())
            e2_instance = e2_instance_type(name=e2_instance_name)
            e1_container.append(e2_instance)
            

    return root