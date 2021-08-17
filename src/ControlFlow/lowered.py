class LoweredStat:
    """
    Lowered statements are low level statements which
    can be directly converted to machine code as well
    as analyzed to extract control flow information.
    """

    def destination(self):
        pass

    def emit_code(self):
        pass


class PrintStat(LoweredStat):
    pass


class ReadStat(LoweredStat):
    pass


class BranchStat(LoweredStat):
    pass


class EmptyStat(LoweredStat):
    pass


class LoadPtrToSymb(LoweredStat):
    pass


class StoreStat(LoweredStat):
    pass


class LoadStat(LoweredStat):
    pass


class LoadImmStat(LoweredStat):
    pass


class BinStat(LoweredStat):
    pass


class UnaryStat(LoweredStat):
    pass


class StatList(LoweredStat):
    pass








