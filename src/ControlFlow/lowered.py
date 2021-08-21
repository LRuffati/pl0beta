import abc


class Codegen(abc.ABC):

    @abc.abstractmethod
    def emit_code(self):
        pass


class LoweredStat(Codegen):
    """
    Lowered statements are low level statements which
    can be directly converted to machine code as well
    as analyzed to extract control flow information.
    """

    def destination(self):
        pass

    def set_label(self, label):
        pass


class PrintStat(LoweredStat):
    def __init__(self, *, src, symtab):
        pass


class ReadStat(LoweredStat):
    def __init__(self, *, dest, symtab):
        pass


class BranchStat(LoweredStat):
    def __init__(self, *, target, symtab, returns=False, condition=None, negcond=False):
        pass


class EmptyStat(LoweredStat):
    def __init__(self, *, symtab):
        pass


class LoadPtrToSymb(LoweredStat):
    def __init__(self, *, dest, symbol, symtab):
        pass


class StoreStat(LoweredStat):
    def __init__(self, *, dest, symbol, symtab):
        pass


class LoadStat(LoweredStat):
    def __init__(self, *, dest, symbol, symtab):
        pass


class LoadImmStat(LoweredStat):
    def __init__(self, *, dest, val, symtab):
        pass


class BinStat(LoweredStat):
    def __init__(self, *, dest, op, srca, srcb, symtab):
        pass


class UnaryStat(LoweredStat):
    def __init__(self, *, dest, op, src, symtab):
        pass


class StatList(LoweredStat):
    def __init__(self, *, children=None, symtab=None):
        pass


class LoweredBlock(LoweredStat):
    def __init__(self, *, symtab, top_level, body, defs):
        pass


class LoweredDef(LoweredStat):
    def __init__(self, *, body, symtab):
        pass


class LowDefList(LoweredStat):
    def __init__(self, *, children):
        pass






