import string
from lark import Lark

class Parser:
    def __init__(self, grammar: string):
        self.parser = Lark(grammar)


    

