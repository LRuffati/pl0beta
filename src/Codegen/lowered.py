import abc
from typing import Optional as Opt

from src.utils.exceptions import IRException
from src.utils.markers import Codegen, DataLayout
from src.IR.symbols import SymbolTable, Symbol
from src.ControlFlow.DataLayout import GlobalSymbolLayout, LocalSymbolLayout
from src.ControlFlow.BBs import BasicBlock


class LoweredStat(Codegen):
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

    def get_label(self) -> Opt[Symbol]:
        return self.label

    def get_used(self) -> set[Symbol]:
        try:
            s = self.use_set.copy()
            return s
        except AttributeError:
            return set()

    def get_defined(self) -> set[Symbol]:
        try:
            return self.def_set.copy()
        except AttributeError:
            return set()


class PrintStat(LoweredStat):
    def __init__(self, *, src, symtab):
        super().__init__()
        self.src = src
        self.symtab = symtab
        self.use_set = {src}

    def __repr__(self):
        return f"{repr(self.label)+': ' if self.label else ''}print {self.src}"


class ReadStat(LoweredStat):
    def __init__(self, *, dest, symtab):
        super().__init__(dest=dest)
        self.symtab = symtab
        self.def_set = {dest}

    def __repr__(self):
        return f"{repr(self.label)+': ' if self.label else ''}{self.dest} <- read"


class BranchStat(LoweredStat):
    def __init__(self, *, target, symtab, returns=False, condition=None, negcond=False):
        self.target = target
        self.symtab = symtab
        self.rets = returns
        self.condition = condition
        self.negcond = negcond
        super().__init__()
        if self.condition is not None:
            self.use_set = {self.condition}

    def __repr__(self):
        cond = ""
        if self.condition is not None:
            cond = f"if {'not' if self.negcond else ''}{self.condition}"
        if self.rets:
            return f"{repr(self.label)+': ' if self.label else ''}call {self.target} {cond}"
        else:
            return f"{repr(self.label)+': ' if self.label else ''}jump to {self.target} {cond}"


class EmptyStat(LoweredStat):
    def __init__(self, *, symtab):
        super().__init__()
        self.symtab = symtab

    def __repr__(self):
        return f"{self.label}:"


class LoadPtrToSymb(LoweredStat):
    def __init__(self, *, dest, symbol, symtab):
        super().__init__(dest=dest)
        self.symbol = symbol
        self.symtab = symtab
        self.use_set = {self.symbol}
        self.def_set = {self.dest}

    def __repr__(self):
        return f"{repr(self.label)+': ' if self.label else ''}{self.dest} <- ADDR[{self.symbol}]"


class StoreStat(LoweredStat):
    def __init__(self, *, dest, symbol, symtab):
        super().__init__(dest=dest)
        self.symbol = symbol
        self.symtab = symtab
        if self.dest.alloct == 'reg':
            self.use_set = {symbol, dest}
        else:
            self.def_set = {dest}
            self.use_set = {symbol}

    def __repr__(self):
        if self.dest.alloct == 'reg':
            return f"{repr(self.label)+': ' if self.label else ''}{self.dest} <- {self.symbol}"
        else:
            return f"{repr(self.label)+': ' if self.label else ''}MEM[{self.dest}] <- {self.symbol}"


class LoadStat(LoweredStat):
    def __init__(self, *, dest, symbol, symtab):
        super().__init__(dest=dest)
        self.symbol = symbol
        self.symtab = symtab
        # TODO: add def/use sets
        if self.dest.alloct != 'reg':
            raise IRException("Load not to a register")
        self.use_set = {self.symbol}
        self.def_set = {self.dest}

    def __repr__(self):
        return f"{repr(self.label)+': ' if self.label else ''}{self.dest} <- {self.symbol}"


class LoadImmStat(LoweredStat):
    def __init__(self, *, dest, val, symtab):
        super().__init__(dest=dest)
        self.val = val
        self.symtab = symtab
        self.def_set = {self.dest}

    def __repr__(self):
        return f"{repr(self.label)+': ' if self.label else ''}{self.dest} <- IMM[{self.val}]"


class BinStat(LoweredStat):
    def __init__(self, *, dest, op, srca, srcb, symtab):
        super(BinStat, self).__init__(dest=dest)
        self.op = op
        self.srca = srca
        self.srcb = srcb
        self.symtab = symtab
        self.def_set = {self.dest}
        self.use_set = {self.srcb, self.srca}

    def __repr__(self):
        return f"{repr(self.label)+': ' if self.label else ''}{self.dest} <- {self.srca} '{self.op}' {self.srcb}"


class UnaryStat(LoweredStat):
    def __init__(self, *, dest, op, src, symtab):
        super(UnaryStat, self).__init__(dest=dest)
        self.op = op
        self.src = src
        self.symtab = symtab
        self.def_set = {self.dest}
        self.use_set = {self.src}

    def __repr__(self):
        return f"{repr(self.label)+': ' if self.label else ''}{self.dest} <- '{self.op}' {self.src}"


class StatList(LoweredStat):
    def __init__(self, *, children=None, symtab=None):
        self.children = []
        dest = None
        self.function: Opt[Symbol] = None # if function is None after the full
                                          # tree has been lowered then it is the
                                          # global function

        i: LoweredStat
        for i in children:
            dest = i.destination()
            if isinstance(i, StatList):
                if lab := i.get_label():
                    labSt = EmptyStat(symtab=symtab)
                    labSt.set_label(lab)
                    self.children.append(labSt)
                self.children.extend(i.children)
            else:
                self.children.append(i)

        super(StatList, self).__init__(dest=dest)
        self.symtab = symtab

    def to_bbs(self) -> list[BasicBlock]:
        bbs = []
        bb = BasicBlock(self.function, self.symtab)
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
        labSt = EmptyStat(symtab=self.symtab)
        labSt.set_label(label)
        self.children.insert(0, labSt)

    def get_defined(self) -> set[Symbol]:
        return set()

    def get_used(self) -> set[Symbol]:
        s = set()
        for ins in self.children:
            s.update(ins.get_used())
        return s

    def bind_to_func(self, function: Symbol):
        self.function = function

    def __repr__(self):
        return f"Statlist{f' of {self.function}' if self.function else ''} " \
               f"of {len(self.children)} statements"


class LoweredBlock(LoweredStat, DataLayout):
    def __init__(self, *, symtab, top_level, body, defs):
        super(LoweredBlock, self).__init__()
        self.symtab: SymbolTable = symtab
        self.top_lev = top_level
        self.body: StatList = body
        self.defs: LowDefList = defs
        # ^ Info from lowering
        # v Info from analysis
        self.local_vars_space = None

    def perform_data_layout(self):
        """
        Perform layout of the local variables (and possibly args), assign global if
        self.top_lev is asserted

        Then perform the data layout of all defined functions
        :return: None
        """
        if self.top_lev:
            prefix = "_g_"

            var: Symbol
            for var in self.symtab:
                if var.stype.size == 0:
                    continue
                var.set_alloc_info(GlobalSymbolLayout(prefix+var.name, var.stype.size//8))
        else:
            prefix = "_l_"
            offs = 0
            for var in self.symtab:
                if var.stype.size == 0:
                    continue
                bsize = var.stype.size // 8
                offs -= bsize
                var.set_alloc_info(LocalSymbolLayout(prefix + var.name,
                                                     offs,
                                                     bsize,
                                                     self.symtab.lvl))

        i: LoweredDef
        for i in self.defs.defs:
            i.perform_data_layout()
        return


class LoweredDef(LoweredStat, DataLayout):
    def __init__(self, *, body, symtab, func: Symbol):
        super(LoweredDef, self).__init__()
        self.body: LoweredBlock = body
        self.symtab = symtab
        self.function = func
        self.body.body.bind_to_func(self.function)

    def perform_data_layout(self):
        self.body.perform_data_layout()


class LowDefList(LoweredStat):
    def __init__(self, *, children):
        super(LowDefList, self).__init__()
        self.defs: list[LoweredDef] = children
