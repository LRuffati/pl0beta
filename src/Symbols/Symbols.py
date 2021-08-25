from functools import reduce

from MixedTrees.src.MixedTrees import MixedTree
from src.utils.markers import Codegen


class SymbolTable:
    def __init__(self, *args, parent=None):
        self.lst = list(args)
        self.par = parent
        if self.par is None:
            self.lvl = 0
        else:
            self.lvl = self.par.lvl + 1

    def append(self, symb):
        self.lst.append(symb)

    def lookup(self, targ: str, direct=True):
        for s in self.lst:
            if s.name == targ:
                if direct:
                    return s
                if self.lvl == 0:
                    return s  # global vars
                else:
                    raise NotImplementedError("Need to implement properly indirect "
                                              "lookup so that the symbol knows it "
                                              "references a different stack frame "
                                              "during codegen")
        if self.par is not None:
            return self.par.lookup(targ, direct=False)
        print(f"Lookup for {targ} failed in {self}")
        return None

    def create_local(self) -> 'SymbolTable':
        return SymbolTable(parent=self)

    def __iter__(self):
        return iter(self.lst[:])

    def get_global(self) -> 'SymbolTable':
        v = self
        while v.lvl != 0:
            v = v.par
        return v

    def get_global_symbols(self):
        g = self.get_global()
        syms = []

        s: Symbol
        for s in g:
            if s.stype not in [TYPENAMES['function'], TYPENAMES['label']]:
                syms.append(s)
        return syms


class Type:
    def __init__(self, name, size, basetype, qualifiers=None):
        if qualifiers is None:
            qualifiers = []
        self.qual_list = qualifiers

        self.size = size
        self.basetype = basetype

        if name is None:
            name = self.default_name()
        self.name = name

    def default_name(self):
        n = ''
        if 'unsigned' in self.qual_list:
            n += 'u'
        n += 'int'
        n += repr(self.size)
        n += '_t'
        return n


class LabelType(Type):
    def __init__(self):
        super().__init__('label', 0, 'Label', [])
        self.ids = 0

    def __call__(self, target=None):
        self.ids += 1
        return Symbol(name='label_' + repr(self.ids), stype=self, value=target)


class FunctionType(Type):
    def __init__(self):
        super().__init__('function', 0, 'Function', [])


class ArrayType(Type):
    def __init__(self, name, dims, basetype: Type):
        self.dims = dims
        super().__init__(name,
                         reduce(lambda a, b: a * b, dims) * basetype.size,
                         basetype)


class PointerType(Type):
    def __init__(self, ptr_to: Type):
        super().__init__('&' + ptr_to.name, 32, 'Int', ['unsigned'])
        self.pointed_type = ptr_to


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


class Symbol(MixedTree, Codegen):
    """Mixed tree as a base class is necessary since it's a node of a tree"""

    def __init__(self, name, stype, value=None, alloct='auto'):
        self.name = name
        self.stype: Type = stype
        self.value = value
        self.alloct = alloct
        self.allocinfo = None

    def set_alloc_info(self, allocinfo):
        self.allocinfo = allocinfo

    def __repr__(self):
        val = ''
        if type(self.value) is str:
            val = self.value

        base = self.alloct + ' ' + self.stype.name + ' ' + \
               self.name + val

        if self.allocinfo is not None:
            base += "; " + repr(self.allocinfo)
        return base

    # TODO: the codegen for a local/global/inherited symbol will have
    #       to be handled differently