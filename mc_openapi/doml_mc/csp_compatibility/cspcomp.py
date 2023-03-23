from itertools import groupby
import re
import requests
from mc_openapi.doml_mc.imc import IntermediateModelChecker
from mc_openapi.doml_mc.intermediate_model.metamodel import DOMLVersion


IEC_API = 'https://iec.ci.piacere.digital.tecnalia.dev/services/iecbackend/api/root-services/catalogue'

def check_csp_compatibility(model: IntermediateModelChecker, doml_version: DOMLVersion):
    if doml_version != DOMLVersion.V2_2 and doml_version != DOMLVersion.V2_2_1:
        print("Unsupported DOML version!")

    all_json = requests.get(IEC_API).json()

    all_json = [
        {
            'name': x['serviceName'],
            'class': x['serviceClass']['serviceClassName'],
            'props': x['serviceAttributeValues']
        }
        for x in all_json
    ]

    def filterByClass(name: str):
        return [vm for vm in all_json if vm['class'] == name]

    def groupByProvider(elems: list):
        def flatten_properties(el):
            for p in el['props']:
                el[p['serviceAttributeType']['name'].lower()] = p['serviceAttributeValue'] or None
            el.pop('props', None)
            return el

        elems = [flatten_properties(elem) for elem in elems]

        return { k: list(v) for k, v in groupby(sorted(elems, key=lambda elem: elem['provider']), lambda elem: elem['provider'])}


    # Catalog IEC Elements
    iec_vms = groupByProvider(filterByClass('Virtual Machine'))
    iec_stos = groupByProvider(filterByClass('Storage'))
    iec_dbs = groupByProvider(filterByClass('Database'))

    # DOML IM Elements
    im_elems = model.values()

    compnodes = [cn for cn in im_elems if re.match(r"infrastructure_(ComputingNode|Container|PhysicalComputingNode|VirtualMachine)", cn.class_)]
    locations = [lc for lc in im_elems if lc.class_ == 'infrastructure_Location']

    # print(compnodes)
    # print(locations)

    # for each provider
    #   check if the available elements have all the properties of doml elements
    #   if not, mark provider as unsupported and report the unsupported element and its value

    for provider, avail_vms in iec_vms.items():
        print(f'==={provider}===')
        for cn in compnodes:
            # attributes are list|None!
            name = cn.attributes.get('commons_DOMLElement::name')
            cpu_count = cn.attributes.get('infrastructure_ComputingNode::cpu_count')
            memory_mb = cn.attributes.get('infrastructure_ComputingNode::memory_mb')
            location = cn.associations.get('infrastructure_ComputingNode::location')
            region = None
            zone = None
            if location:
                location = model[list(location)[0]]
                region = location.attributes.get('infrastructure_Location::region')
                zone = location.attributes.get('infrastructure_Location::zone')
            # not in IEC
            # arch = cn.attributes.get('infrastructure_ComputingNode::architecture')
            # os = cn.attributes.get('infrastructure_ComputingNode::os')

            print(f'---{name[0]}---')

            valid_configs = avail_vms

            if cpu_count:
                valid_configs = [
                    avm for avm in valid_configs 
                    if (int(avm['virtual cpu cores']) == cpu_count[0] if cpu_count else False)
                ]
            
            if memory_mb:
                valid_configs = [
                    avm for avm in valid_configs 
                    if (float(avm['memory']) * 1000 == float(memory_mb[0]) if memory_mb else False)
                ]

            if region:
                valid_configs = [
                    avm for avm in valid_configs 
                    if (avm['region'] == region[0] if region else False)
                ]
            
            if zone:
                valid_configs = [
                    avm for avm in valid_configs 
                    if (avm['zone'] == zone[0] if zone else False)
                ]

            # print(valid_configs)            


            
