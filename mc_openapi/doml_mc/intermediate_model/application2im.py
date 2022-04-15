from ..model.application import Application, ApplicationComponent
from .._utils import merge_dicts

from .types import IntermediateModel
from .doml_element import DOMLElement


def application_to_im(app: Application) -> IntermediateModel:
    def app_comp_to_im(
        app_comp: ApplicationComponent,
    ) -> IntermediateModel:
        comp_elem = DOMLElement(
            name=app_comp.name,
            class_=app_comp.typeId,
            attributes={"commons_DOMLElement::name": app_comp.name},
            associations={
                "application_SoftwarePackage::consumedInterfaces": {
                    f"{cn}_{ifacen}"
                    for cn, ifacens in app_comp.consumedInterfaces.items()
                    for ifacen in ifacens
                },
                "application_SoftwarePackage::exposedInterfaces": {
                    f"{app_comp.name}_{ifacen}"
                    for ifacen in app_comp.exposedInterfaces
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
            for ifacen, iface in app_comp.exposedInterfaces.items()
            for elem_n in [f"{app_comp.name}_{ifacen}"]
        }

        return {app_comp.name: comp_elem} | iface_elems

    return merge_dicts(app_comp_to_im(comp) for comp in app.children.values())
