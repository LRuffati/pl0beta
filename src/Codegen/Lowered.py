from typing import Optional as Opt

import src
from src.Symbols.Symbols import PrintFun, ReadFun
from src.utils.Exceptions import IRException
from src.utils.markers import Lowered


class LoweredStat(Lowered):
    """
    Lowered statements are low level statements which
    can be directly converted to machine code as well
    as analyzed to extract control flow information.
    """

    def __init__(self, *, dest=None, label=None):
        self.dest = dest
        self.label = label

    def destination(self):
        return self.dest

    def set_label(self, label):
        self.label = label

    def get_label(self) -> Opt['Symbol']:
        return self.label

    def get_used(self) -> set['Symbol']:
        try:
            s = self.use_set.copy()
            return s
        except AttributeError:
            return set()

    def get_defined(self) -> set['Symbol']:
        try:
            return self.def_set.copy()
        except AttributeError:
            return set()

    def prepare_layout(self, *,
                       layout: 'StackLayout' = None,
                       symtab: 'SymbolTable' = None,
                       regalloc: 'AllocInfo' = None,
                       bblock: 'BasicBlock' = None,
                       container: 'LoweredBlock' = None) -> Opt['StackLayout']:

        spild = layout.get_section('spill')

        used_vars = self.get_used()
        def_vars = self.get_defined()
        vars = used_vars | def_vars
        vars_regs = [i for i in vars if i.alloct == 'reg']
        for i in vars_regs:
            if regalloc.is_spilled_var(i):
                spild.grow(symb=i)


class BranchStat(LoweredStat):
    """
    Jumps (conditionally) to a label (expecting to return)
    If it expects to return it's a function call
    """
    def __init__(self, *,
                 target,
                 returns=False,
                 condition: 'RegisterSymb' = None,
                 negcond=False):
        self.target: 'Symbol' = target
        # If the call is to a function the level of the symbol shows how many
        # frame pointers to provide. Level 0 the parent is global so 0, level 1
        # I need to give the pointer to the stack of the level 0 function it was defined
        # inside of etc

        self.rets: bool = returns
        self.condition: 'RegisterSymb' = condition
        self.negcond: bool = negcond
        super().__init__()
        if self.condition is not None:
            self.use_set = {self.condition}

    def __repr__(self):
        cond = ""
        if self.condition is not None:
            cond = f"if {'not ' if self.negcond else ''}{self.condition}"
        if self.rets:
            return f"{repr(self.label) + ': ' if self.label else ''}call {self.target} {cond}"
        else:
            return f"{repr(self.label) + ': ' if self.label else ''}jump to {self.target} {cond}"

    def prepare_layout(self, *,
                       layout: 'StackLayout' = None,
                       symtab: 'SymbolTable' = None,
                       regalloc: 'AllocInfo' = None,
                       bblock: 'BasicBlock' = None,
                       container: 'LoweredBlock' = None) -> Opt['StackLayout']:

        super().prepare_layout(layout=layout,
                               symtab=symtab,
                               regalloc=regalloc,
                               bblock=bblock,
                               container=container)
        if not self.rets:
            return

        regsave = layout.get_section('regsave_out')
        args = layout.get_section('args_out')

        args.set_size(self.target.level)
        regsave.set_size(len(self.get_regs_to_save(bblock, regalloc)))
        return

    def get_regs_to_save(self, bblock: 'BasicBlock', regalloc: 'AllocInfo') -> list:
        return [0, 1, 2, 3]

    def emit_code(self, code: 'Code', *,
                  layout: 'StackLayout' = None,
                  symtab: 'SymbolTable' = None,
                  regalloc: 'AllocInfo' = None,
                  bblock: 'BasicBlock' = None,
                  container: 'LoweredBlock' = None) -> Opt['Code']:
        if self.rets:
            # TODO: code to save registers and pass arguments
            #   use as scratch registers one of the saved ones
            pass

        if self.condition:
            # TODO: conditional jump
            pass
        else:
            # TODO: unconditional jump
            pass

        if self.rets:
            # TODO: restore registers
            pass


class PrintStat(BranchStat):
    """
    Prints the value contained in register src

    Assembly:
        save_regs
        a0 := reg[src]
        call print
        restore regs
    """
    def __init__(self, *, src: 'RegisterSymb'):
        super().__init__(returns=True, target=PrintFun)
        self.src = src
        self.use_set = {src}

    def __repr__(self):
        return f"{repr(self.label) + ': ' if self.label else ''}print {self.src}"

    def emit_code(self, code: 'Code', *,
                  layout: 'StackLayout' = None,
                  symtab: 'SymbolTable' = None,
                  regalloc: 'AllocInfo' = None,
                  bblock: 'BasicBlock' = None,
                  container: 'LoweredBlock' = None) -> Opt['Code']:

        # Do not use the Branch method default, use the inheritance only
        # for the methods to save registers and for the layout preparation
        raise NotImplementedError


class ReadStat(BranchStat):
    """
    Reads some value into the register of dest
    Assembly:
        save_regs
        call read
        reg[dest] := a0
        restore_regs
    """
    def __init__(self, *, dest: 'RegisterSymb'):
        super().__init__(returns=True, target=ReadFun)
        LoweredStat.__init__(self, dest=dest)
        self.def_set = {dest}

    def __repr__(self):
        return f"{repr(self.label) + ': ' if self.label else ''}{self.dest} <- read"

    def emit_code(self, code: 'Code', *,
                  layout: 'StackLayout' = None,
                  symtab: 'SymbolTable' = None,
                  regalloc: 'AllocInfo' = None,
                  bblock: 'BasicBlock' = None,
                  container: 'LoweredBlock' = None) -> Opt['Code']:
        # Do not use BranchStat method since I need to exclude the a0 register
        # from restoring
        raise NotImplementedError


class EmptyStat(LoweredStat):
    def __init__(self):
        super().__init__()

    def __repr__(self):
        return f"{self.label}:"

    def emit_code(self, code: 'Code', *,
                  layout: 'StackLayout' = None,
                  symtab: 'SymbolTable' = None,
                  regalloc: 'AllocInfo' = None,
                  bblock: 'BasicBlock' = None,
                  container: 'LoweredBlock' = None) -> Opt['Code']:
        if self.label:
            code.label(self.label.name)


class LoadPtrToSymb(LoweredStat):
    """
    Loads in dest the pointer to the symbol in memory
    """
    def __init__(self, *, dest, symbol):
        super().__init__(dest=dest)
        self.symbol = symbol
        self.use_set = {self.symbol}
        self.def_set = {self.dest}

    def __repr__(self):
        return f"{repr(self.label) + ': ' if self.label else ''}{self.dest} <- ADDR[{self.symbol}]"


class StoreStat(LoweredStat):
    """
    TODO
    """
    def __init__(self, *, dest, symbol):
        super().__init__(dest=dest)
        self.symbol = symbol
        if self.dest.alloct == 'reg':
            self.use_set = {symbol, dest}
        else:
            self.def_set = {dest}
            self.use_set = {symbol}

    def __repr__(self):
        if self.dest.alloct == 'reg':
            return f"{repr(self.label) + ': ' if self.label else ''}{self.dest} <- {self.symbol}"
        else:
            return f"{repr(self.label) + ': ' if self.label else ''}MEM[{self.dest}] <- {self.symbol}"


class LoadStat(LoweredStat):
    """
    Loads from memory into dest
    If symbols is a register it loads the value at the address in symbol
    If it's a variable it loads the variable from memory
    """
    def __init__(self, *, dest, symbol):
        super().__init__(dest=dest)
        self.symbol = symbol
        if self.dest.alloct != 'reg':
            raise IRException("Load not to a register")
        self.use_set = {self.symbol}
        self.def_set = {self.dest}

    def __repr__(self):
        if self.symbol.alloct == 'reg':
            return f"{repr(self.label) + ': ' if self.label else ''}{self.dest} <- MEM[*{self.symbol}]"
        else:
            return f"{repr(self.label) + ': ' if self.label else ''}{self.dest} <- MEM[{self.symbol}]"



class LoadImmStat(LoweredStat):
    """
    Places an immediate value in the register
    """
    def __init__(self, *, dest, val):
        super().__init__(dest=dest)
        self.val = val
        self.def_set = {self.dest}

    def __repr__(self):
        return f"{repr(self.label) + ': ' if self.label else ''}{self.dest} <- IMM[{self.val}]"


class BinStat(LoweredStat):
    """
    Binary operation between two registers
    """
    def __init__(self, *, dest: 'RegisterSymb', op, srca, srcb):
        super(BinStat, self).__init__(dest=dest)
        self.op = op
        self.srca: 'RegisterSymb' = srca
        self.srcb: 'RegisterSymb' = srcb
        self.def_set = {self.dest}
        self.use_set = {self.srcb, self.srca}

    def __repr__(self):
        return f"{repr(self.label) + ': ' if self.label else ''}{self.dest} <- {self.srca} '{self.op}' {self.srcb}"

    def emit_code(self, code: 'Code', *,
                  layout: 'StackLayout' = None,
                  symtab: 'SymbolTable' = None,
                  regalloc: 'AllocInfo' = None,
                  bblock: 'BasicBlock' = None,
                  container: 'LoweredBlock' = None) -> Opt['Code']:
        srca = self.srca.gen_load(code, layout, symtab, regalloc)
        srcb = self.srcb.gen_load(code, layout, symtab, regalloc)
        dest = self.dest.get_register(regalloc)

        # TODO: Stuff
        # Stuff
        # Stuff

        self.dest.gen_store(code, layout, symtab, regalloc)
        return


class UnaryStat(LoweredStat):
    """
    Unary operation on a register
    """
    def __init__(self, *, dest, op, src):
        super(UnaryStat, self).__init__(dest=dest)
        self.op = op
        self.src = src
        self.def_set = {self.dest}
        self.use_set = {self.src}

    def __repr__(self):
        return f"{repr(self.label) + ': ' if self.label else ''}{self.dest} <- '{self.op}' {self.src}"


class StatList(LoweredStat):
    def __init__(self, *, children=None):
        self.children = []
        dest = None
        self.function: Opt['Symbol'] = None  # if function is None after the full
        # tree has been lowered then it is the
        # global function

        i: LoweredStat
        for i in children:
            dest = i.destination()
            if isinstance(i, StatList):
                if lab := i.get_label():
                    labSt = EmptyStat()
                    labSt.set_label(lab)
                    self.children.append(labSt)
                self.children.extend(i.children)
            else:
                self.children.append(i)

        super(StatList, self).__init__(dest=dest)

    def to_bbs(self, symtab: 'SymbolTable') -> list['BasicBlock']:
        bbs = []
        bb = src.ControlFlow.BBs.BasicBlock(self.function, symtab)
        for instr in self.children:
            compl, bb = bb.append(instr)
            if compl:
                if len(bbs):
                    bbs[-1].add_succs(next=compl)
                bbs.append(compl)

        if not bb.is_empty():
            bb.finalize()
            if len(bbs):
                bbs[-1].add_succs(next=bb)
            bbs.append(bb)
        return bbs

    def set_label(self, label):
        labSt = EmptyStat()
        labSt.set_label(label)
        self.children.insert(0, labSt)

    def get_defined(self) -> set['Symbol']:
        return set()

    def get_used(self) -> set['Symbol']:
        s = set()
        for ins in self.children:
            s.update(ins.get_used())
        return s

    def bind_to_func(self, function: 'Symbol'):
        self.function = function

    def __repr__(self):
        return f"Statlist{f' of {self.function}' if self.function else ''} " \
               f"of {len(self.children)} statements"


if __name__ == '__main__':
    Symbol = src.Symbols.Symbols.Symbol
    SymbolTable = src.Symbols.Symbols.SymbolTable
    BasicBlock = src.ControlFlow.BBs.BasicBlock
    StackLayout = src.Codegen.FrameUtils.StackLayout
    AllocInfo = src.Allocator.Regalloc.AllocInfo
    LoweredBlock = src.ControlFlow.CodeContainers.LoweredBlock
    Code = src.Codegen.Code.Code
    RegisterSymb = src.Symbols.Symbols.RegisterSymb
