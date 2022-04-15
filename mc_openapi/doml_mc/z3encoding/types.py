from z3 import DatatypeRef, DatatypeSortRef

Refs = dict[str, DatatypeRef]
SortAndRefs = tuple[DatatypeSortRef, Refs]
