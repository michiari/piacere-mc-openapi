from .mc import ModelChecker   # noqa: F401
from .mc_result import MCResult, MCResults   # noqa: F401
from .intermediate_model.metamodel import DOMLVersion, init_metamodels   # noqa: F401
from .xmi_parser.doml_model import init_doml_rsets
from .xmi_parser.special_parsers import init_special_parsers
from .main import init_model, verify_csp_compatibility, verify_model, synthesize_model

__all__ = ["ModelChecker", "MCResult", "MCResults", "DOMLVersion"]

# Load metamodels
init_metamodels()

# Load ecores
init_doml_rsets()

# Generate SpecialParsers
init_special_parsers()
