

from mc_openapi.doml_mc.intermediate_model.doml_element import DOMLElement, IntermediateModel
from mc_openapi.doml_mc.intermediate_model.metamodel import DOMLVersion

import re

class CSPCompatibilityValidator:
    def __init__(self, keypairs, architectures, regions) -> None:
        self.valid_keypairs = keypairs
        self.valid_architectures = architectures
        self.valid_regions = regions
        pass

    def check(self, model: IntermediateModel, doml_version: DOMLVersion) -> list[str]:
        """Returns a list of CSP supported by the model"""
        if doml_version == DOMLVersion.V2_2:
            elems = model.values()
            
            print('=====================================')
            print('========= CSP Compatibility =========')
            print('=====================================')

            # Check KeyPair
            keypairs = [kp for kp in elems if kp.class_ == 'commons_KeyPair']
            print("\n--- Keypairs ---")
            self.check_keypair(keypairs)

            # ComputingNode and inheritors
            print("\n--- Architectures ---")
            compnodes = [cn for cn in elems if re.match(r"infrastructure_(ComputingNode|Container|PhysicalComputingNode|VirtualMachine)", cn.class_)]
            self.check_computing_nodes(compnodes)

            # Locations
            print("\n--- Locations ---")
            locations = [lc for lc in elems if lc.class_ == 'infrastructure_Location']
            self.check_locations(locations)
        else:
            raise "Unsupported DOML version (<2.2) for CSP Compatibility check"

    def check_keypair(self, keypairs: list[DOMLElement]):
        for kp in keypairs:
                algorithm = kp.attributes.get('commons_KeyPair::algorithm')
                bits = kp.attributes.get('commons_KeyPair::bits')
                # For each vendor, check if there's at least one supported configuration
                for vendor, vkps in self.valid_keypairs.items():
                    valid_algorithms = []
                    valid_bits = []

                    if algorithm:
                        valid_algorithms = [vkp.get('algorithm').lower() == algorithm[0].lower() for vkp in vkps]
                    if bits:
                        def comp_bits(b, bits):
                            if b is None:
                                return True
                            b =  b.split('-')
                            if len(b) > 1:
                                lb = b[0]
                                ub = b[1]
                                return (int(lb) <= bits if lb != '*' else True) and (bits <= int(ub) if ub != '*' else True)
                            else:
                                return b[0] == bits
                        valid_bits = [comp_bits(vkp.get('bits'), bits[0]) for vkp in vkps]
                
                    if not any(valid_algorithms):
                        print(f"{kp.user_friendly_name} 'algorithm' not compatible with: {vendor}")
                    if not any(valid_bits):
                        print(f"{kp.user_friendly_name} 'bits' not compatible with: {vendor}")
    
    def check_computing_nodes(self, elems: list[DOMLElement]):
        for el in elems:
            arch = el.attributes.get('infrastructure_ComputingNode::architecture')
            # os = el.attributes.get('infrastructure_ComputingNode::os')
            # cpu_count = el.attributes.get('infrastructure_ComputingNode::cpu_count')
            # memory_mb = el.attributes.get('infrastructure_ComputingNode::memory_mb')

            if arch:
                for vendor, varchs in self.valid_architectures.items():
                    valid_archs = [arch[0] == varch for varch in varchs]
                    if not any(valid_archs):
                        print(f"{el.user_friendly_name} 'architecture' not compatible with: {vendor}")

            # OS requires probably a fine-handling of <os>, <flavor/version>
    
    def check_locations(self, locations: list[DOMLElement]):
        for loc in locations:
            reg = loc.attributes.get('infrastructure_Location::region')
            
            if reg:
                for vendor, vregs in self.valid_regions.items():
                    valid_regs = [reg[0] == vreg for vreg in vregs]
                    if not any(valid_regs):
                        print(f"{loc.user_friendly_name or 'A'} 'region' (value: {reg[0]}) not compatible with: {vendor}")
                    

