class RequirementException(Exception):
    message: str
    def __repr__(self) -> str:
        return self.message

class RequirementMissingKeyException(RequirementException):
    def __init__(self, key_type: str, key: str, close_matches: list[str], *args: object) -> None:
        super().__init__(*args)
        fix_syntax = lambda x: x.replace("_", ".").replace("::", "->")
        key = fix_syntax(key)
        close_matches = list(map(fix_syntax, close_matches))
        self.message = f"Error: no {key_type} found named '{key}'.\n"
        if close_matches:
            self.message += "Perhaps you meant...\n"
            self.message += "".join([f"- '{match}'\n" for match in close_matches])

class RequirementBadSyntaxException(RequirementException):
    def __init__(self, line: int, col: int, message: str, *args: object) -> None:
        super().__init__(*args)
        self.message = f"Syntax Error at Ln {line}, Col {col}:\n{message}"
