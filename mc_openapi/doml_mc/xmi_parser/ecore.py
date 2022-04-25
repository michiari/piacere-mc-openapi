import sys
from typing import Callable

from pyecore.ecore import EEnumLiteral, EObject, EOrderedSet, EClass

from ..intermediate_model.doml_element import (
    Associations, Attributes, DOMLElement, IntermediateModel,
    Values, parse_associations, parse_attributes
)
from ..intermediate_model.metamodel import MetaModel


class SpecialParser:
    def __init__(self, parsers: dict[tuple[str, str], Callable]):
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
        self.visited: set[str] = set()

    def parse_elayer(self, doc: EObject) -> IntermediateModel:
        self.parse_eobject(doc)
        return self.im

    def parse_eobject(self, doc: EObject) -> str:
        # TODO: deal with properties in a better way
        name = doc.name if hasattr(doc, "name") else doc.key
        if name in self.visited:
            return name
        self.visited.add(name)

        mm_class = ELayerParser.mangle_eclass_name(doc.eClass)

        # Get all attributes
        raw_attrs: Attributes = {}
        for eAttr in doc.eClass.eAllAttributes():
            val = getattr(doc, eAttr.name)
            if val is not None:
                if self.special_parser and self.special_parser.is_special(doc.eClass.name, eAttr.name):
                    raw_attrs |= self.special_parser.parse_special(doc.eClass.name, eAttr.name, val)
                else:
                    if isinstance(val, str) or isinstance(val, int) or isinstance(val, bool):
                        raw_attrs[eAttr.name] = val
                    elif isinstance(val, EEnumLiteral):
                        raw_attrs[eAttr.name] = str(val)
                    elif isinstance(val, EOrderedSet):
                        print("Attribute", eAttr.name, "of multiplicity > 1 not supported yet.", file=sys.stderr)
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
            name=name, class_=mm_class, attributes=attrs, associations=assocs
        )
        return name

    def mangle_eclass_name(eClass: EClass) -> str:
        return eClass.ePackage.name + "_" + eClass.name
