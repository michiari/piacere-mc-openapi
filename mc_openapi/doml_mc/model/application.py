from dataclasses import dataclass
from .types import Attributes


@dataclass
class Application:
    name: str
    children: dict[str, "ApplicationComponent"]


@dataclass
class ApplicationComponent:
    typeId: str
    name: str
    consumedInterfaces: list["ApplicationInterface"]
    exposedInterfaces: list["ApplicationInterface"]
    attributes: Attributes


@dataclass
class ApplicationInterface:
    endPoint: str
    componentName: str
    typeId: str


# @dataclass
# class Property:
#     key: str
#     value: str
#     typeId: str
#
# def parse_property(doc: ecore.Property) -> Property:
#     return Property(
#         key=doc.key,
#         value=doc.value,
#         typeId=doc.type
#     )
