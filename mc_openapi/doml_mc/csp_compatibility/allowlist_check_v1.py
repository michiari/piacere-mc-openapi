

from mc_openapi.doml_mc.intermediate_model.doml_element import DOMLElement, IntermediateModel
from mc_openapi.doml_mc.intermediate_model.metamodel import DOMLVersion
from difflib import SequenceMatcher

import re

class CSPCompatibilityValidator:
    def __init__(self, data: dict) -> None:
        self.data = data

    def check(self, model: IntermediateModel, doml_version: DOMLVersion) -> dict[str, list]:
        """Returns a list of CSP supported by the model"""

        ret = {}

        # Check KeyPair
        keypairs = self.check_keypair(model)
        if len(keypairs) > 1:
            ret['keypairs'] = keypairs
        # ComputingNode and inheritors
        arch, os, minreq = self.check_computing_nodes(model)
        if len(arch) > 1:
            ret['arch'] = arch
        if len(os) > 1:
            ret['os'] = os
        if len(minreq) > 1:
            ret['minreq'] = minreq

        return ret

    def check_keypair(self, model: IntermediateModel):
        elems = model.values()
        keypairs = [kp for kp in elems if kp.class_ == 'commons_KeyPair']
        TABLE = [['KeyPair', 'Algorithm', *self.data['keypair'].keys()]]
        for kp in keypairs:
            name = kp.user_friendly_name
            algorithm = kp.attributes.get('commons_KeyPair::algorithm')
            bits = kp.attributes.get('commons_KeyPair::bits')
            # For each vendor, check if there's at least one supported configuration
            if algorithm is not None and len(algorithm) > 0:
                algorithm = algorithm[0].upper()
                ROW = [name, algorithm]
                for _, valid_algos in self.data['keypair'].items():
                    value = '✅' if algorithm in valid_algos else '❌'
                    ROW.append(value)
                TABLE.append(ROW)
        return TABLE
    
    def check_computing_nodes(self, model: IntermediateModel):
        elems = model.values()
        compnodes = [cn for cn in elems if re.match(r"infrastructure_(ComputingNode|Container|PhysicalComputingNode|VirtualMachine)", cn.class_)]
        ARCH_TABLE = [['Node', 'Arch', *self.data['arch'].keys()]]
        OS_TABLE = [['Node', 'OS', *self.data['os'].keys()]]
        MINREQ_TABLE = [['Node', *self.data['minimum_setup'].keys()]]

        VALID_OS_MATCH_PERCENT = 0.33

        for el in compnodes:
            name = el.user_friendly_name or el.attributes.get('commons_DOMLElement::name') or f'[{el.class_}]'
            arch = el.attributes.get('infrastructure_ComputingNode::architecture')
            os = el.attributes.get('infrastructure_ComputingNode::os')
            # cpu_count = el.attributes.get('infrastructure_ComputingNode::cpu_count')
            # memory_mb = el.attributes.get('infrastructure_ComputingNode::memory_mb')

            # CHECK ARCH
            if arch and len(arch) > 0:
                arch = arch[0].upper()
                ROW = [name, arch]
                for _, valid_archs in self.data['arch'].items():
                    valid_archs = [v.upper() for v in valid_archs]
                    value = '✅' if arch in valid_archs else '❌'
                    ROW.append(value)
                ARCH_TABLE.append(ROW)

            # CHECK OS
            if os and len(os) > 0:
                os = os[0].upper()
                ROW = [name, os]
                for _, valid_os in self.data['os'].items():
                    valid_os = [distro.upper() for os_family in valid_os for distro in valid_os[os_family]]
                    compatible_os = [v for v in valid_os if v in os or os in v]
                    alt_compatible_os = [(v, SequenceMatcher(None, v, os).ratio()) for v in valid_os if SequenceMatcher(None, v, os).ratio() > VALID_OS_MATCH_PERCENT]
                    alt_compatible_os = sorted(alt_compatible_os, key=lambda x: x[1])
                    value = any(compatible_os)
                    value = '✅' if value else '❌' if len(alt_compatible_os) == 0 else '❓' 
                    if len(compatible_os) > 0:
                        value += f' ({compatible_os[0].lower()})'
                    if value == '❓':
                        alt_os_name, alt_os_ratio = alt_compatible_os[0]
                        value += f' ({alt_os_name.lower()}, {alt_os_ratio*100:.{1}f}%)'
                    ROW.append(value)
                OS_TABLE.append(ROW)
               
            # CHECK MINIMUM REQUIREMENTS FOR CSP
            ROW = [name]
            for vendor, reqs in self.data['minimum_setup'].items():
                CHECKS = {}
                for req in reqs:
                    if isinstance(req, list):
                        try:
                            dep = list(el.associations.get(req[0]))[0]
                            dep = model[dep]
                            CHECKS[str(req)] = dep.associations.get(req[1]) is not None or el.attributes.get(req[1]) is not None
                        except:
                            CHECKS[str(req)] = False
                    if isinstance(req, str):
                        CHECKS[req] = el.associations.get(req) is not None or el.attributes.get(req) is not None
                
                all_req_valid = all([v for v in CHECKS.values()])
                value = ['✅' if all_req_valid else '❌']
                if not all_req_valid:
                    value += [
                        re.sub(r"\s*,\s*", " -> ", k)
                        .replace("_", ".", 1)
                        .replace("::", ".")
                        .replace("[", "")
                        .replace("]", "")
                        .replace("'", "")
                        for k, v in CHECKS.items() 
                        if v is False
                    ]
                ROW.append(value)
            MINREQ_TABLE.append(ROW)

        return ARCH_TABLE, OS_TABLE, MINREQ_TABLE
    
       

    
