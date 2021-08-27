from functools import reduce

import src
from MixedTrees.src.MixedTrees import MixedTree
from src.utils.Exceptions import IRException
from src.utils.markers import Codegen


class SymbolTable:
    """
    A symbol table is a collection of named symbols which is visible within
    a block and all blocks within the block

    If a symbol table is not the global symtab then it has a parent, all
    tables are chained through their parents to the global symbol table

    Each table has a level starting with 0 for the global one and increasing
    as the distance from the global symbol table
    """
    def __init__(self, *args, parent=None):
        self.lst = list(args)
        self.par = parent
        if self.par is None:
            self.lvl = 0
        else:
            self.lvl = self.par.lvl + 1

    def append(self, symb: 'Symbol'):
        if symb.level is not None:
            raise IRException('Symbol already in some symtab')
        symb.set_level(self.lvl)
        symb.level = self.lvl
        self.lst.append(symb)

    def lookup(self, targ: str, direct=True):
        for s in self.lst:
            if s.name == targ:
                if direct:
                    return s
                if self.lvl == 0:
                    return s  # global vars
                else:
                    return s # TODO should I handle them differently?
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
        """

        :param name: The name of the type
        :param size: The size in bits
        :param basetype:
        :param qualifiers:
        """
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
    """
    A symbol is a reference to some object or address, named symbols are
    those included in symbol tables while unnamed or register symbols represent
    a register value

    A symbol (named and unnamed alike) has:
    + a name
    + an stype denoting the type of the value it represents
    + a value (not sure the function)
    + an allocation type
    + an allocation info object describing its location in memory
    + a level representing the level of the symbol table it was defined in

    """
    # Mixed tree as a base class is necessary since it's a node of a tree

    def __init__(self, name, stype, value=None, alloct='auto'):
        self.name = name
        self.stype: Type = stype
        self.value = value
        self.alloct = alloct
        self.allocinfo: 'SymbolLayout' = None
        self.level = None

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

    def get_register(self, regalloc: 'AllocInfo') -> int:
        pass

    def gen_load(self,
                 code: 'Code',
                 frame: 'StackLayout',
                 symtab: 'SymbolTable',
                 regalloc: 'AllocInfo',
                 dest_symb: 'RegisterSymb' = None) -> int:
        """
        This function is to be called when using a symbol as a source operand or when
        loading a variable to a register

        If the symbol was a ephemeral symbol representing a register it'll check with the regalloc information
        if it needs to be loaded from the spill. If it wasn't spilled no new code is needed and it can be used as is

        If it was spilled the code for loading the variable into the appropriate register will be generated

        In either of the cases above the return value is the numeric id of the register in which the value is
        located

        If the symbol is a global or local variable the dest_symb is necessary and identifies
        the register in which to load the value. In this case I need to get the concrete register
        from the regalloc (the register might be a spilled register, so I need to materialize it
        but I don't need to issue a load since I'll overwrite the value anyway)

        Once I have the actual register I can load the symbol in the register, either as
        a label for global symbol, a simple offset from fp for local variables or, if it's
        a nested local variable:
        ```
        dest <- fp + [offset of the nested stack address]
        dest <- LOAD dest [offset of the local variable in the native frame]
        ```

        The return value will be the concrete register

        :param symtab:
        :param regalloc:
        :param code:
        :param frame:
        :param dest_symb:
        :return:
        """
        pass

    def gen_store(self,
                  code: 'Code',
                  frame: 'StackLayout',
                  symtab: 'SymbolTable',
                  regalloc: 'AllocInfo',
                  source_symb: 'RegisterSymb' = None):
        """
        This function is to be called on the symbol being used as a destination of an
        operation or when storing a value in a variable

        If the symbol represents a register it'll check if it needs to be spilled to
        memory and if so it'll emit the code needed.

        If the symbol is a variable the source_symb parameter is required and I need
        to call the gen_load on it to retrieve the actual value

        I then need to issue the store which can be:
        + to a global symbol if it's a global variable
        + to an offset of the local fp if it's a local variable native to the frame
        + to an offset of an address which I need to load
            TODO: this third option requires a further register to hold the intermediate
                value, I can either use the register I would for a spilled variable,
                obtaining the value from the regalloc, or reserve a register
                rs <- val
                ---


        :param code:
        :param frame:
        :param symtab:
        :param regalloc:
        :param source_symb:
        :return:
        """
        pass

    def set_level(self, lvl):
        self.level = lvl


class RegisterSymb(Symbol):
    """
    A class specific for register temporaries
    """
    def set_level(self, lvl):
        raise NotImplementedError("Trying to bind a register symbol to symtab")

    def set_alloc_info(self, allocinfo):
        raise NotImplementedError("Register symbols don't have allocation info")



ReadFun = Symbol('__pl0_read', TYPENAMES['function'])
ReadFun.set_level(0)
PrintFun = Symbol('__pl0_print', TYPENAMES['function'])
PrintFun.set_level(0)

if __name__ == '__main__':
    Code = src.Codegen.Code.Code
    StackLayout = src.Codegen.FrameUtils.StackLayout
    AllocInfo = src.Allocator.Regalloc.AllocInfo
    SymbolLayout = src.ControlFlow.DataLayout.SymbolLayout
