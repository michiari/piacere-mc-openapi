from dataclasses import dataclass
from pyecore.ecore import EObject

from ..model.application import Application, ApplicationComponent, ApplicationInterface


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

def parse_application(doc: EObject) -> Application:
    # TODO: consider full ApplicationComponent class hierarchy
    def parse_application_interface(doc: EObject, componentName: str) -> ApplicationInterface:
        return ApplicationInterface(
            name=doc.endPoint,
            componentName=componentName,
            typeId="application_" + doc.eClass.name,
            endPoint=doc.endPoint,
        )
    def parse_application_component(doc: EObject, interfaces: dict) -> ApplicationComponent:
        consumed = {}
        for cif in doc.consumedInterfaces:
            cifProvider = interfaces[cif.endPoint].componentName
            if cifProvider in consumed:
                consumed[cifProvider].append(cif.endPoint)
            else:
                consumed[cifProvider] = [cif.endPoint]

        return ApplicationComponent(
            name=doc.name,
            typeId="application_" + doc.eClass.name,
            consumedInterfaces=consumed,
            exposedInterfaces={
                intdoc.endpoint: parse_application_interface(
                    intdoc, doc.name
                )
                for intdoc in doc.exposedInterfaces
            },
        )

    # Parse all interfaces first
    interfaces = {
        iface.name: parse_application_interface(iface)
        for comp in doc.components
        for iface in comp.exposedInterfaces
    }

    return Application(
        name=doc.name,
        children={
            compdoc.name: parse_application_component(compdoc, interfaces)
            for compdoc in doc.components
        },
    )
