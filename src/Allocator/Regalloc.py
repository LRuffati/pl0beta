from collections import namedtuple

VarLiveInfo = namedtuple("VarLiveInfo", ["var", "defined", "kill", "interv"])
SPILL_FLAG = 9999


class AllocInfo:
    """
    This class holds informations on the variables and their allocations
    to registers. It is passed to the code generation unit
    """

    def __init__(self, vartoreg: dict['Symbol', int], numspill: int, nregs: int):
        self.var_to_reg: dict['Symbol', int] = vartoreg
        self.numspill = numspill
        self.nregs = nregs

        self.vartospill_frameoffset = dict()
        self.spillregi = 0
        self.spillframeoffseti = 0

    def update(self, other_ra: 'AllocInfo'):
        self.var_to_reg.update(other_ra.var_to_reg)
        self.numspill += other_ra.numspill

    def spill_room(self):
        return self.numspill * 4

    def dematerialize_spilled_var_if_necessary(self, var: 'Symbol'):
        if self.var_to_reg[var] >= self.nregs - 2:
            self.var_to_reg[var] = SPILL_FLAG

    def materialize_spilled_if_necessary(self, var: 'Symbol'):
        if self.var_to_reg[var] != SPILL_FLAG:
            if self.var_to_reg[var] >= self.nregs - 2:
                return True
            return False

        self.var_to_reg[var] = self.spillregi + self.nregs - 2
        self.spillregi = (self.spillregi + 1) % 2

        if not (var in self.vartospill_frameoffset):
            self.vartospill_frameoffset[var] = self.spillframeoffseti
            self.spillframeoffseti += 4
        return True


class RegisterAllocator:
    """
    This is the base class for the possible register allocators.
    Its core function is to take in a control flow graph and to
    return an AllocInfo object
    """

    def __call__(self, cfg: 'CFG', root: 'LoweredBlock') -> 'AllocInfo':
        raise NotImplementedError()


class LinearScanRegAlloc(RegisterAllocator):
    """

    """

    def __init__(self, nregs):
        """

        :param nregs:
        """
        self.nreg = nregs
        self.varliveness: list[VarLiveInfo] = []
        self.all_vars = []
        self.var_to_reg = {}

    def compute_liveness_intervarls(self, cfg: 'CFG'):
        inst_index = 0
        min_gen = {}
        max_use = {}
        vars = set()

        bb: 'BasicBlock'
        for bb in cfg:
            inst: 'LoweredStat'
            for inst in bb.statements:
                kill = LinearScanRegAlloc.remove_non_regs(inst.get_defined())
                used = LinearScanRegAlloc.remove_non_regs(inst.get_used())

                for var in kill:
                    if var not in min_gen:
                        min_gen[var] = inst_index
                        max_use[var] = inst_index
                for var in used:
                    max_use[var] = inst_index

                vars |= kill | used
                inst_index += 1

        for var in vars:
            gen = min_gen[var]
            kill = max_use[var]
            self.varliveness.append(VarLiveInfo(var, gen, kill, range(gen, kill)))
        self.varliveness.sort(key=lambda x: x.defined)
        self.all_vars = list(vars)

    def __call__(self, cfg: 'CFG', root: 'LoweredBlock' = None) -> AllocInfo:
        self.compute_liveness_intervarls(cfg)

        live: list[VarLiveInfo] = []
        freeregs = set(range(0, self.nreg - 2))
        numspill = 0

        for livei in self.varliveness:
            start = livei.defined
            i = 0
            while i < len(live):
                notLiveCand = live[i]
                if notLiveCand.kill < start:
                    live.pop(i)
                    freeregs.add(self.var_to_reg[notLiveCand.var])
                else:
                    # When I pop I don't increment since it implicitly increments the value
                    # relative to the rest of the array
                    i += 1

            if len(freeregs) == 0:
                tospill = live[-1]
                if tospill.kill > livei.kill:
                    self.var_to_reg[livei.var] = self.var_to_reg[tospill.var]
                    self.var_to_reg[tospill.var] = SPILL_FLAG
                    live.pop(-1)
                    live.append(livei)
                else:
                    self.var_to_reg[livei.var] = SPILL_FLAG
                numspill += 1
            else:
                self.var_to_reg[livei.var] = freeregs.pop()
                live.append(livei)
            live.sort(key=lambda li: li.kill)

        return AllocInfo(self.var_to_reg, numspill, self.nreg)

    @staticmethod
    def remove_non_regs(varset: set['Symbol']):
        return {var for var in varset if var.alloct == 'reg'}
