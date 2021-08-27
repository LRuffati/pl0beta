from collections import namedtuple

import src

VarLiveInfo = namedtuple("VarLiveInfo", ["var", "defined", "kill", "interv"])
VarLiveInfo.__doc__ = """A structure holding the information on the liveness interval of a given
symbol. 
`var` is the symbol, `defined` is the instruction it was defined at, `kill` the last instruction to use it"""
SPILL_FLAG = 9999


class AllocInfo:
    """
    This class holds informations on the variables and their allocations
    to registers. It is passed to the code generation unit

    + var_to_reg: a dictionary from a symbol to the register in which to place it
    + numspill: the number of variables that get spilled in the whole program
    + nregs: the number of registers
    + vartospill_frameoffset: the locations of the variables which get spilled
        relative to the base of the spill section
    + TODO: spillframeoffseti: the size of the currently spilled variables
    """

    def __init__(self, vartoreg: dict['Symbol', int], numspill: int, nregs: int):
        self.var_to_reg: dict['Symbol', int] = vartoreg
        self.numspill: int = numspill
        self.nregs: int = nregs

        self.vartospill_frameoffset = dict()
        self.spillregi = 0
        self.spillframeoffseti = 0

    def update(self, other_ra: 'AllocInfo'):
        self.var_to_reg.update(other_ra.var_to_reg)
        self.numspill += other_ra.numspill

    def spill_room(self):
        return self.numspill * 4

    def is_spilled_var(self, var: 'Symbol'):
        reg = self.var_to_reg.get(var, -1)
        return reg >= self.nregs - 2

    def dematerialize_spilled_var_if_necessary(self, var: 'Symbol'):
        """
        Flags a spilled symbol as spilled after it had been temporarily loaded into a
        register
        :param var:
        :return:
        """
        if self.var_to_reg[var] >= self.nregs - 2:
            self.var_to_reg[var] = SPILL_FLAG

    def materialize_spilled_if_necessary(self, var: 'Symbol'):
        """
        Checks if a variable is supposed to be spilled
        If it is and
        :param var:
        :return:
        """
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
    This class implements the linear scan method for register allocation
    """

    def __init__(self, nregs, cfg_iterator):
        """

        :param nregs: the number of registers available
        :param cfg_iterator: a class constructing a deterministic iterator
        over a control flow graph. It must receive a 'CFG' and return an
        iterator over the basic blocks
        """
        self.nreg = nregs
        self.varliveness: list[VarLiveInfo] = []
        self.all_vars = []
        self.var_to_reg = {}
        self.iterclass = cfg_iterator

    def compute_liveness_intervarls(self, cfg: 'CFG'):
        inst_index = 0
        min_gen = {}
        max_use = {}
        vars_seen = set()

        bb: 'BasicBlock'
        for bb in self.iterclass(cfg):
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

                vars_seen |= kill | used
                inst_index += 1

        for var in vars_seen:
            gen = min_gen[var]
            kill = max_use[var]
            self.varliveness.append(VarLiveInfo(var, gen, kill, range(gen, kill)))
        self.varliveness.sort(key=lambda x: x.defined)
        self.all_vars = list(vars_seen)

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
                numspill += 1  # TODO: this provides a very conservative estimate of the space needed
            else:
                self.var_to_reg[livei.var] = freeregs.pop()
                live.append(livei)
            live.sort(key=lambda li: li.kill)

        return AllocInfo(self.var_to_reg, numspill, self.nreg)

    @staticmethod
    def remove_non_regs(varset: set['Symbol']):
        return {var for var in varset if var.alloct == 'reg'}


if __name__ == '__main__':
    Symbol = src.Symbols.Symbols.Symbol
    CFG = src.ControlFlow.CFG.CFG
    BasicBlock = src.ControlFlow.BBs.BasicBlock
    LoweredStat = src.Codegen.Lowered.LoweredStat
    LoweredBlock = src.ControlFlow.CodeContainers.LoweredBlock
