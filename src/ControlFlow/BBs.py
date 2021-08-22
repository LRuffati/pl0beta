from typing import Optional as Opt

import src.ControlFlow.lowered as lwr
from src.IR.symbols import Symbol, TYPENAMES
from src.utils.exceptions import CFGException


class BasicBlock:
    def __init__(self):
        self.statements: list[lwr.LoweredStat] = []
        self.label_in: Opt[Symbol] = None
        self.next: Opt['BasicBlock'] = None # the next
        self.next_lab: Opt[Symbol] = None
        self.target: Opt['BasicBlock'] = None # the target of a branch instruction
        self.target_lab: Opt[Symbol] = None

        # v properties for later
        self.kill: Opt[set[Symbol]] = None
        self.gen: Opt[set[Symbol]] = None

        self.live_in: Opt[set[Symbol]] = None
        self.live_out: Opt[set[Symbol]] = None

        self.total_vars_used: Opt[int] = None

    def append(self, instr: 'lwr.LoweredStat') -> tuple[Opt['BasicBlock'], 'BasicBlock']:
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

        if isinstance(instr, lwr.BranchStat) and not instr.rets:
            self.finalize()
            self.target_lab = instr.target
            new = BasicBlock()
            return self, new
        return None, self

    def finalize(self):
        """
        To call when no more instructions are to be added to the block
        :return:
        """
        if self.label_in is None:
            lab = TYPENAMES['label']()
            self.add_label(lab)

        self.live_in = set()
        self.live_out = set()

        self.kill = set()
        self.gen = set()

        self.statements: list[lwr.LoweredStat]
        for i in self.statements:
            used = i.get_used()
            defined = i.get_defined()
            used -= self.kill
            self.gen |= used
            self.kill |= defined

        self.total_vars_used = len(self.gen | self.kill)

    def add_label(self, label: Symbol):
        if self.label_in:
            raise CFGException("Adding label to already labeled block")
        self.label_in = label

    def add_succs(self, *, next: Opt['BasicBlock'] = None, alt: Opt['BasicBlock'] = None):
        if next:
            self.next = next
            self.next_lab = next.label_in
        if alt:
            if self.target_lab != alt.label_in:
                raise CFGException("Adding target with incorrect label")
            self.target = alt

    def successors(self) -> list['BasicBlock']:
        """

        :return: The successors to the block
        """
        l = []
        if self.next is not None:
            l.append(self.next)
        if self.target is not None:
            l.append(self.target)
        return l

    def get_follower_labels(self) -> set[Symbol]:
        s = set()
        if self.target_lab:
            s.add(self.target_lab)
        if self.next_lab:
            s.add(self.next_lab)
        return s

    def liveness_iter(self):
        pass

    def is_empty(self) -> bool:
        try:
            _ = self.statements[0]
            return False
        except IndexError:
            return True

    def remove_useless_next(self):
        last_instr = self.statements[-1]
        if isinstance(last_instr, lwr.BranchStat):
            if last_instr.condition is None:
                self.next = None
                self.next_lab = None

    def func_calls(self) -> set[Symbol]:
        s = set()
        for i in self.statements:
            if isinstance(i, lwr.BranchStat):
                if i.rets:
                    s.add(i.target)
        return s


    def __repr__(self):
        if self.label_in:
            out = []
            if self.next_lab:
                out.append(f"next: {repr(self.next_lab)}")
            if self.target_lab:
                out.append(f"target: {repr(self.target_lab)}")

            return f"BasicBlock: {repr(self.label_in)} -> {' | '.join(out)}"
        return f"BasicBlock_{len(self.statements)}_instrs"