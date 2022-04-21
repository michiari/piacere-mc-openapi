from ..model.application import Application, ApplicationComponent
from .._utils import merge_dicts

from .metamodel import MetaModel
from .types import IntermediateModel
from .doml_element import DOMLElement, parse_attributes


def application_to_im(app: Application, mm: MetaModel) -> IntermediateModel:
    def app_comp_to_im(app_comp: ApplicationComponent) -> IntermediateModel:
        attrs = parse_attributes(app_comp.attributes, app_comp.typeId, mm)
        attrs["commons_DOMLElement::name"] = app_comp.name
        comp_elem = DOMLElement(
            name=app_comp.name,
            class_=app_comp.typeId,
            attributes=attrs,
            associations={
                "application_SoftwarePackage::consumedInterfaces": {
                    f"{iface.componentName}_{iface.endPoint}"
                    for iface in app_comp.consumedInterfaces
                },
                "application_SoftwarePackage::exposedInterfaces": {
                    f"{app_comp.name}_{iface.endPoint}"
                    for iface in app_comp.exposedInterfaces
                },
            },
        )

        iface_elems = {
            elem_n: DOMLElement(
                name=elem_n,
                class_="application_SoftwareInterface",
                attributes={
                    "commons_DOMLElement::name": elem_n,
                    "application_SoftwareInterface::endPoint": iface.endPoint,
                },
                associations={},
            )
            for iface in app_comp.exposedInterfaces
            for elem_n in [f"{app_comp.name}_{iface.endPoint}"]
        }

        return {app_comp.name: comp_elem} | iface_elems

    return merge_dicts(app_comp_to_im(comp) for comp in app.children.values())
