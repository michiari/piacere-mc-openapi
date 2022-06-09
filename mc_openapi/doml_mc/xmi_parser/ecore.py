import sys
from typing import Callable

from pyecore.ecore import EEnumLiteral, EObject, EOrderedSet, EClass

from ..intermediate_model.doml_element import (
    Associations, Attributes, DOMLElement, IntermediateModel,
    Values, parse_associations, parse_attributes
)
from ..intermediate_model.metamodel import MetaModel


class SpecialParser:
    def __init__(self, mm: MetaModel, parsers: dict[tuple[str, str], Callable]):
        superclasses: dict[str, list[tuple[str, Callable]]] = {}
        for (clsname, attrname), attrparser in parsers.items():
            if clsname in superclasses:
                superclasses[clsname].append((attrname, attrparser))
            else:
                superclasses[clsname] = [(attrname, attrparser)]

        while superclasses:
            new_superclasses = {}
            for classname, mmclass in mm.items():
                if mmclass.superclass in superclasses:
                    attrs_parsers = superclasses[mmclass.superclass]
                    new_superclasses[classname] = attrs_parsers
                    parsers |= {(classname, attrname): attrparser for attrname, attrparser in attrs_parsers}
            superclasses = new_superclasses

        self.parsers = parsers

    def is_special(self, class_name: str, attr_name: str) -> bool:
        return (class_name, attr_name) in self.parsers

    def parse_special(self, class_name: str, attr_name: str, avalue: Values) -> Attributes:
        parser = self.parsers[(class_name, attr_name)]
        return parser(avalue)


class ELayerParser:
    def __init__(self, mm: MetaModel, special_parser=None):
        self.mm = mm
        self.special_parser = special_parser
        self.im: dict[str, "DOMLElement"] = {}
        self.visited: set[int] = set()
        self.nextUniqueId = 0

    def parse_elayer(self, doc: EObject) -> IntermediateModel:
        self.parse_eobject(doc)
        return self.im

    def parse_eobject(self, doc: EObject) -> str:
        doc_id = id(doc)
        name = "elem_" + str(doc_id)
        if doc_id in self.visited:
            return name
        self.visited.add(doc_id)

        mm_class = ELayerParser.mangle_eclass_name(doc.eClass)

        # Get all attributes
        raw_attrs: Attributes = {}
        for eAttr in doc.eClass.eAllAttributes():
            val = getattr(doc, eAttr.name)
            if val is not None:
                if self.special_parser and self.special_parser.is_special(mm_class, eAttr.name):
                    raw_attrs |= self.special_parser.parse_special(mm_class, eAttr.name, val)
                else:
                    if isinstance(val, str) or isinstance(val, int) or isinstance(val, bool):
                        raw_attrs[eAttr.name] = [val]
                    elif isinstance(val, EEnumLiteral):
                        raw_attrs[eAttr.name] = [str(val)]
                    elif isinstance(val, EOrderedSet):
                        raw_attrs[eAttr.name] = [str(v) if isinstance(v, EEnumLiteral) else v for v in val]
                    else:
                        print("Attribute", eAttr.name, "has value", val, "of unexpected type.", file=sys.stderr)
        attrs = parse_attributes(raw_attrs, mm_class, self.mm)

        # Get all references and process them
        raw_assocs: Associations = {}
        for eRef in doc.eClass.eAllReferences():
            targets = getattr(doc, eRef.name)
            if targets:
                if eRef.upper == 1:
                    raw_assocs[eRef.name] = {self.parse_eobject(targets)}
                else:
                    raw_assocs[eRef.name] = {self.parse_eobject(t) for t in targets}
        assocs = parse_associations(raw_assocs, mm_class, self.mm)

        self.im[name] = DOMLElement(
            id_=name, class_=mm_class, attributes=attrs, associations=assocs
        )
        return name

    def getUniqueName(self):
        name = f"__generated_name__{self.nextUniqueId}"
        self.nextUniqueId += 1
        return name

    def mangle_eclass_name(eClass: EClass) -> str:
        return eClass.ePackage.name + "_" + eClass.name
