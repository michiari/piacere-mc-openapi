from typing import Union
from dataclasses import dataclass

from .metamodel import (
    MetaModel,
    get_mangled_attribute_name,
    get_mangled_association_name,
)

Values = Union[str, int, bool]
Attributes = dict[str, Values]
Associations = dict[str, set[str]]


@dataclass
class DOMLElement:
    name: str
    class_: str
    # the keys of the `attributes`/`associations` dicts are
    # attribute/association names mangled with the type that declares them,
    # e.g., `"application_SoftwarePackage::isPersistent"`.
    attributes: Attributes
    associations: Associations


IntermediateModel = dict[str, "DOMLElement"]


def parse_attributes(raw_attributes: Attributes, comp_class: str, mm: MetaModel) -> Attributes:
    attributes: Attributes = {}
    for k, v in raw_attributes.items():
        man = get_mangled_attribute_name(mm, comp_class, k)
        if v is None:
            raise RuntimeError("Supplied with None attribute value.")
        attributes[man] = v
    return attributes


def parse_associations(raw_associations: Associations, comp_class: str, mm: MetaModel) -> Associations:
    associations: Associations = {}
    for k, v in raw_associations.items():
        man = get_mangled_association_name(mm, comp_class, k)
        if not v:
            raise RuntimeError("Supplied with empty association.")
        associations[man] = v
    return associations


def reciprocate_inverse_associations(
    im: IntermediateModel,
    invs: list[tuple[str, str]],
) -> None:
    """
    ### Effects
    This procedure is effectful on `im`.
    """
    # A dict for inverse lookup where inverse relationships are mapped both
    # ways.
    inv_dict = dict(invs) | {an2: an1 for an1, an2 in invs}
    for ename, elem in im.items():
        for aname, atgts in elem.associations.items():
            if aname in inv_dict:
                for atgt in atgts:
                    im[atgt].associations[inv_dict[aname]] = im[
                        atgt
                    ].associations.get(inv_dict[aname], set()) | {ename}
