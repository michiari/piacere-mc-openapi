from z3 import ExprRef, ModelRef
from typing import Optional
from mc_openapi.doml_mc.intermediate_model import IntermediateModel

def get_user_friendly_name(
    intermediate_model: IntermediateModel,
    model: ModelRef,
    const: ExprRef
) -> Optional[str]:
    z3_elem = model[const]
    if z3_elem is not None:
        im_elem = intermediate_model.get(str(z3_elem))
        if im_elem is not None:
            return im_elem.user_friendly_name
    return None
