from mc_openapi.doml_mc.intermediate_model.metamodel import DOMLVersion, MetaModels
from pprint import pprint
from itertools import groupby

DOCS_PATH = lambda version: f"docs/reference_{version}.rst"

DOML_VERSIONS = [v for v in DOMLVersion]

with open(DOCS_PATH('index'), 'w') as findex:
    print("DOML Reference", file=findex)
    print("==============\n", file=findex)
    print("For a comprehensive list of all the classes, attributes and associations supported in the DOML Model Checker and DOMLR, please consult one of the following pages.\n", file=findex)

    for version in DOML_VERSIONS:
        v_name = f':doc:`Reference for DOML {version.value} <reference_{version.value}>`'
        print(v_name, file=findex)
        print('-'*len(v_name), file=findex)

        with open(DOCS_PATH(version.value), 'w') as f:
            print(f"DOML {version.value} Reference", file=f)
            print("=============================\n", file=f)
            
            MM = MetaModels[version]
            # ITEM => (package, class, assoc, attrs)
            ITEMS = [(*(k.split("_", 1)), v.superclass, v.associations, v.attributes) for k, v in MM.items()] 
            # PKG => CLASS => {ASSOC, ATTRS}
            ITEMS = {k: [dict(zip(("name", "superclass", "assocs", "attrs"), (x[1], x[2], x[3], x[4]))) for x in v] for k, v in groupby(ITEMS, key=lambda x: x[0])}

            for pkg, clss in ITEMS.items():
                print(f'\n{pkg}', file=f)
                print('^'*(len(pkg)), file=f)
                for cls in sorted(clss, key=lambda x: x.get('name')):
                    name = cls.get('name')
                    supcls = cls.get('superclass')
                    print(f'\n.. _{version.value}_{pkg}_{name}:', file=f)
                    print(f'\n{name}', file=f)
                    print('"'*(len(name)), file=f)
                    if supcls:
                        supcls_name = supcls.split("_", 1)[1]
                        print(f'*Inherits from* :ref:`{supcls_name} <{version.value}_{supcls}>`\n', file=f)
                    if (cls.get('assocs')):
                        print(f'* Associations:', file=f)
                        for assoc_k, assoc_v in cls.get('assocs').items():
                            dest_cls = assoc_v.class_.split("_", 1)[1]
                            print(f'\t* ``{assoc_k}`` → {dest_cls} [{assoc_v.multiplicity[0]}..{assoc_v.multiplicity[1]}]', file=f)
                    if (cls.get('attrs')):
                        print(f'* Attributes:', file=f)
                        for attr_k, attr_v in cls.get('attrs').items():
                            print(f'\t* ``{attr_k}`` [{attr_v.type}]', file=f)
            print("\n\n", file=f)

        print(f"Generated new reference for DOML {version.value} in {DOCS_PATH(version.value)}")