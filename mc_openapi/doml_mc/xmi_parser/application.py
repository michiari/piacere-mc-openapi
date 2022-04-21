from pyecore.ecore import EClass, EObject

from ..model.application import Application, ApplicationComponent, ApplicationInterface


def ecore_issubclass(child: EClass, parentName: str) -> bool:
    return child.name == parentName \
        or any(ecore_issubclass(superEClass, parentName) for superEClass in child.eSuperTypes)


def ecore_isinstance(obj: EObject, eClassName: str) -> bool:
    return ecore_issubclass(obj.eClass, eClassName)


def parse_application(doc: EObject) -> Application:
    def parse_application_interface(doc: EObject, componentName: str) -> ApplicationInterface:
        return ApplicationInterface(
            endPoint=doc.endPoint,
            componentName=componentName,
            typeId="application_" + doc.eClass.name,
        )

    def parse_application_component(doc: EObject, interfaces: dict[str, "ApplicationInterface"]) -> ApplicationComponent:
        attrs = {}
        if ecore_isinstance(doc, "SoftwareComponent"):
            attrs["isPersistent"] = doc.isPersistent
            if doc.licenseCost:
                attrs["licenseCost"] = str(doc.licenseCost)  # FIXME: add float support in the model
            if doc.configFile:
                attrs["configFile"] = doc.configFile
        if ecore_isinstance(doc, "SaaS"):
            if doc.licenseCost:
                attrs["licenseCost"] = doc.licenseCost
        # TODO: add properties
        return ApplicationComponent(
            name=doc.name,
            typeId="application_" + doc.eClass.name,
            consumedInterfaces=[
                interfaces[iface.endPoint]
                for iface in doc.consumedInterfaces
            ],
            exposedInterfaces=[
                interfaces[iface.endPoint]
                for iface in doc.exposedInterfaces
            ],
            attributes=attrs
        )

    # Parse all interfaces first
    interfaces = {
        iface.endPoint: parse_application_interface(iface, comp.name)
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
