from dataclasses import dataclass
from typing import cast, Literal, Optional, Union

import networkx as nx

from .._utils import merge_dicts

Multiplicity = tuple[Literal["0", "1"], Literal["1", "*"]]


class AttributeNotFound(Exception):
    pass


class AssociationNotFound(Exception):
    pass


@dataclass
class DOMLClass:
    name: str
    superclass: Optional[str]
    attributes: dict[str, "DOMLAttribute"]
    associations: dict[str, "DOMLAssociation"]


@dataclass
class DOMLAttribute:
    name: str
    type: Literal["Boolean", "Integer", "String", "GeneratorKind"]
    multiplicity: Multiplicity
    default: Optional[list[Union[str, int, bool]]]


@dataclass
class DOMLAssociation:
    name: str
    class_: str
    multiplicity: Multiplicity


MetaModel = dict[str, DOMLClass]


def parse_metamodel(mmdoc: dict) -> MetaModel:
    def parse_class(cname: str, cdoc: dict) -> DOMLClass:
        def parse_mult(
            mults: Literal["0..1", "0..*", "1", "1..*"]
        ) -> Multiplicity:
            if mults == "0..1":
                return ("0", "1")
            elif mults == "1":
                return ("1", "1")
            elif mults == "1..*":
                return ("1", "*")
            else:
                return ("0", "*")

        def parse_attribute(aname: str, adoc: dict) -> DOMLAttribute:
            # sourcery skip: merge-comparisons
            type_: str = adoc["type"]
            assert (
                type_ == "Boolean"
                or type_ == "Integer"
                or type_ == "String"
                or type_ == "GeneratorKind"
            )
            mults: str = adoc.get("multiplicity", "0..*")
            assert (
                mults == "0..1"
                or mults == "0..*"
                or mults == "1"
                or mults == "1..*"
            )
            default = adoc.get("default")
            return DOMLAttribute(
                name=aname,
                type=type_,  # type: ignore[arg-type]
                multiplicity=parse_mult(mults),  # type: ignore[arg-type]
                default=default if default is None or isinstance(default, list) else [default],
            )

        def parse_association(aname: str, adoc: dict) -> DOMLAssociation:
            # sourcery skip: merge-comparisons
            mults: str = adoc.get("multiplicity", "0..*")
            assert (
                mults == "0..1"
                or mults == "0..*"
                or mults == "1"
                or mults == "1..*"
            )
            return DOMLAssociation(
                name=aname,
                class_=adoc["class"],
                multiplicity=parse_mult(mults),  # type: ignore[arg-type]
            )

        return DOMLClass(
            name=cname,
            superclass=cdoc.get("superclass"),
            attributes={
                aname: parse_attribute(aname, adoc)
                for aname, adoc in cdoc.get("attributes", {}).items()
            },
            associations={
                aname: parse_association(aname, adoc)
                for aname, adoc in cdoc.get("associations", {}).items()
            },
        )

    assert set(mmdoc.keys()) <= {
        "commons",
        "application",
        "infrastructure",
        "concrete",
    }

    return merge_dicts(
        {
            prefixed_name: parse_class(prefixed_name, cdoc)
            for cname, cdoc in csdoc.items()
            for prefixed_name in [f"{prefix}_{cname}"]
        }
        for prefix, csdoc in mmdoc.items()
    )


def parse_inverse_associations(doc: dict) -> list[tuple[str, str]]:
    return [
        (inv_of, f"{layer}_{cname}::{aname}")
        for layer, ldoc in doc.items()
        for cname, cdoc in ldoc.items()
        for aname, adoc in cdoc.get("associations", {}).items()
        for inv_of in [adoc.get("inverse_of")]
        if inv_of is not None
    ]


def _find_association_class(
    mm: MetaModel,
    cname: str,
    aname: str,
) -> DOMLClass:
    c = mm[cname]
    if aname in c.associations:
        return c
    elif c.superclass is None:
        raise AssociationNotFound(
            f"Association {aname} not found in subclasses of {cname}."
        )
    else:
        return _find_association_class(mm, c.superclass, aname)


def get_mangled_association_name(
    mm: MetaModel,
    cname: str,
    aname: str,
) -> str:
    return f"{_find_association_class(mm, cname, aname).name}::{aname}"


def get_mangled_attribute_defaults(
    mm: MetaModel,
    cname: str,
) -> dict[str, list[Union[str, int, bool]]]:
    c = mm[cname]
    defaults = {
        f"{cname}::{aname}": a.default
        for aname, a in c.attributes.items()
        if a.default is not None
    }
    if c.superclass is None:
        return defaults
    else:
        return get_mangled_attribute_defaults(mm, c.superclass) | defaults


def _find_attribute_class(
    mm: MetaModel,
    cname: str,
    aname: str,
) -> DOMLClass:
    c = mm[cname]
    if aname in c.attributes:
        return c
    elif c.superclass is None:
        raise AttributeNotFound(
            f"Attribute {aname} not found in subclasses of {cname}."
        )
    else:
        return _find_attribute_class(mm, c.superclass, aname)


def get_mangled_attribute_name(
    mm: MetaModel,
    cname: str,
    aname: str,
) -> str:
    return f"{_find_attribute_class(mm, cname, aname).name}::{aname}"


def get_subclasses_dict(mm: MetaModel) -> dict[str, set[str]]:
    inherits_dg = nx.DiGraph(
        [
            (c.name, c.superclass)
            for c in mm.values()
            if c.superclass is not None
        ]
    )
    inherits_dg.add_nodes_from(mm)
    inherits_dg_trans = cast(
        nx.DiGraph, nx.transitive_closure(inherits_dg, reflexive=True)
    )
    return {cname: set(inherits_dg_trans.predecessors(cname)) for cname in mm}


def get_superclasses_dict(mm: MetaModel) -> dict[str, set[str]]:
    inherits_dg = nx.DiGraph(
        [
            (c.name, c.superclass)
            for c in mm.values()
            if c.superclass is not None
        ]
    )
    inherits_dg.add_nodes_from(mm)
    inherits_dg_trans = cast(
        nx.DiGraph, nx.transitive_closure(inherits_dg, reflexive=True)
    )
    return {cname: set(inherits_dg_trans.successors(cname)) for cname in mm}
