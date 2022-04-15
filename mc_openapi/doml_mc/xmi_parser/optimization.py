from dataclasses import dataclass
from pyecore.ecore import EObject

from ..model.optimization import Optimization

def parse_optimization(doc: EObject) -> Optimization:
    return Optimization(
        typeId="optimization_" + doc.eClass.name,
    )
