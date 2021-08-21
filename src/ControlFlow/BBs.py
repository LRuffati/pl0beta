from typing import Optional as Opt

import src.ControlFlow.lowered
from src.ControlFlow import lowered
#from src.ControlFlow.lowered import LoweredStat, BranchStat
from src.IR.symbols import Symbol


class BasicBlock:
    def __init__(self):
        self.statements: list['LoweredStat'] = []
        self.labels_in: list[Symbol] = []
        self.next: Opt['BasicBlock'] = None # the next
        self.target: Opt['BasicBlock'] = None # the target of a branch instruction
        self.target_lab: Opt[Symbol] = None

        # v properties for later
        self.kill: Opt[set[Symbol]] = None
        self.gen: Opt[set[Symbol]] = None

        self.live_in: Opt[set[Symbol]] = None
        self.live_out: Opt[set[Symbol]] = None

        self.total_vars_used: Opt[int] = None

    def append(self, instr: 'LoweredStat') -> tuple[Opt['BasicBlock'], 'BasicBlock']:
        """
        :param instr:
        :return: a tuple whose first element is a completed BB (if the instruction
                 cause a bb to split and whose second element is the active BB to
                 increment, if the first element is None the second is self
        """
        if lab := instr.get_label():
            if len(self.statements):
                self.finalize()
                compl = self
                new = BasicBlock()
                _, new = new.append(instr)
                return compl, new
            else:
                self.add_label(lab)

        self.statements.append(instr)

        if isinstance(instr, lowered.BranchStat) and not instr.rets:
            self.finalize()
            self.target = instr.target
            new = BasicBlock()
            return self, new
        return None, self

    def finalize(self):
        """
        To call when no more instructions are to be added to the block
        :return:
        """
        if len(self.labels_in)==0:
            # TODO: I should create a new ad-hoc label
            pass
        self.live_in = set()
        self.live_out = set()

        self.kill = set()
        self.gen = set()

        for i in self.statements:
            pass

        # TODO: needs to set the label(s) of the block and the label of the
        #       branch

    def add_label(self, label: Symbol):
        self.labels_in.append(label)

    def add_succs(self, *, next: Opt['BasicBlock'] = None, alt: Opt['BasicBlock'] = None):
        if next:
            self.next = next
        if alt:
            self.target = alt

    def successors(self) -> list[Symbol]:
        """

        :return: The successors to the block
        """

    def liveness_iter(self):
        pass

    def is_empty(self) -> bool:
        try:
            self.statements[0]
            return False
        except IndexError:
            return True

    def remove_useless_next(self):
        last_instr = self.statements[-1]
        if isinstance(last_instr, src.ControlFlow.lowered.BranchStat):
            if last_instr.condition is None:
                self.next = None
