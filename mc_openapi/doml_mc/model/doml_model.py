from dataclasses import dataclass
from typing import Optional

from .application import Application
from .infrastructure import Infrastructure
from .optimization import Optimization
from .concretization import Concretization


@dataclass
class DOMLModel:
    name: str
    description: str
    application: Application
    infrastructure: Infrastructure
    optimization: Optional[Optimization]
    concretizations: dict[str, Concretization]
