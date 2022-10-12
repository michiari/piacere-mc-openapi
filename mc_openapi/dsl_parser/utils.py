from mc_openapi.doml_mc.imc import SMTEncoding, SMTSorts
from z3 import Const, DatatypeRef, ExprRef, FuncDeclRef, SortRef

class UniqueVarStore:
    """This class provides a way to instance a Z3 variable only the first time
       it's called, and subsequent uses of that variable simply retrieve it
       from the store.
    """

    def __init__(self, smtenc: SMTEncoding, sort: SortRef):
        self.vars = dict() # is a dictionary of tuples [ExprRef, bool (is var quantified?)]
        self.encoding = smtenc
        self.sort = sort
    
    def use(self, var_name: str) -> ExprRef:
        """Retrieves a variable with `var_name` from the store.
           If that variable doesn't exists, it is added to the store and returned.
        """
        if self.vars.get(var_name, None) is None:
            self.vars[var_name] = (Const(var_name, self.sort), False)
       
        return self.vars[var_name][0]
    
    def quantify(self, vars: list):
        for var in vars:
            self.vars[str(var)] = (var, True)
        
    def get_free_vars(self) -> list:
        return [var[0] for var in self.vars.values() if var[1] == False]

    def keys(self) -> list[str]:
        return self.vars.keys()

    def clear(self):
        """Clears the store of all saved variables."""
        self.vars.clear()

class RefHandler:
    """A utility class that provides simplified ways to create Z3 Refs.
    """

    def __init__(self, smtenc: SMTEncoding):
        self.encoding = smtenc
    
    def get_element_class(self, const: ExprRef) -> FuncDeclRef:
        return self.encoding.element_class_fun(const)

    def get_class(self, class_name: str) -> DatatypeRef:
        class_name = class_name.replace(".", "_")
        _class = self.encoding.classes.get(class_name, None)
        if _class is not None:
            return _class
        else:
            raise Exception(f"No class named '{class_name}' found.")
            # TODO: Try to suggest the correct class with difflib
            # see: https://docs.python.org/3/library/difflib.html?highlight=get_close_matches#difflib.get_close_matches

    def get_association(self, assoc_name: str) -> DatatypeRef:
        assoc_name = assoc_name.replace(".", "_")
        assoc_name = assoc_name.replace("->", "::")
        assoc = self.encoding.associations.get(assoc_name, None)
        if assoc is not None:
            return assoc
        else:
            raise Exception(f"No association named '{assoc_name}' found.")

    def get_association_rel(self, a: ExprRef, rel: DatatypeRef, b: ExprRef) -> DatatypeRef:
        return self.encoding.association_rel(a, rel, b)

    def get_attribute(self, attr_name: str) -> DatatypeRef:
        attr_name = attr_name.replace(".", "_")
        attr_name = attr_name.replace("->", "::")
        attr = self.encoding.attributes.get(attr_name, None)
        if attr is not None:
            return attr
        else:
            raise Exception(f"No attribute named '{attr_name}' found.")

    def get_attribute_rel(self, a: ExprRef, rel: DatatypeRef, b: ExprRef) -> DatatypeRef:
        return self.encoding.attribute_rel(a, rel, b)

