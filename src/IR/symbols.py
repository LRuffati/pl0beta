from MixedTrees.src import MixedTrees as mxdt

class SymbolTable:
    @classmethod
    def from_tables(cls, *tables):
        """
        Obtain a symbol table by merging multiple symbol tables
        Symbols in later tables overwrite symbols in previous ones
        :param tables:
        :return:
        """

    def append(self, *args, **kwargs):
        print("Appending to symtab: ",args,kwargs)

    def lookup(self, targ: str):
        pass


class Type:
    def __init__(self, *args, **kwargs):
        pass


class LabelType(Type):
    pass


class FunctionType(Type):
    pass


class ArrayType(Type):
    pass


TYPENAMES = {
    'int': Type('int', 32, 'Int'),
    'short': Type('short', 16, 'Int'),
    'char': Type('char', 8, 'Int'),
    'uchar': Type('uchar', 8, 'Int', ['unsigned']),
    'uint': Type('uint', 32, 'Int', ['unsigned']),
    'ushort': Type('ushort', 16, 'Int', ['unsigned']),
    # 'float': Type('float', 32, 'Float'),
    'label': LabelType(),
    'function': FunctionType(),
}
