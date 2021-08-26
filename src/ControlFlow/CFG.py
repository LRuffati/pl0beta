from typing import Optional as Opt

import src
from src.ControlFlow.CodeContainers import LoweredBlock, LoweredDef
from src.utils.Exceptions import CFGException


class CFG:
    def __init__(self, program: 'LoweredBlock'):
        queue = [program]
        glob_stat_lst = None
        self.global_block: Opt['LoweredBlock'] = None
        self.functions: dict['Symbol', 'LoweredBlock'] = {}

        while True:
            try:
                el = queue.pop()
            except IndexError:
                break

            if isinstance(el, LoweredBlock):
                for i in el.defs.lst:
                    i: 'LoweredDef'
                    queue.append(i)
                _ = el.to_bbs()
                if el.function is None:
                    self.global_block = el
            elif isinstance(el, LoweredDef):
                self.functions[el.function] = el.body
                queue.append(el.body)

        blocks_labs: set['Symbol'] = set()
        follows_labs: set['Symbol'] = set()

        bb: 'BasicBlock'
        for bb in self:
            blocks_labs.add(bb.label_in)
            follows_labs |= bb.get_follower_labels()

            if lab_t := bb.target_lab:
                bb.add_succs(alt=self.find_by_lab(lab_t))
            bb.remove_useless_next()

        self.heads_labels = blocks_labs - follows_labs

    def find_by_lab(self, label: 'Symbol') -> 'BasicBlock':
        bb: 'BasicBlock'
        for bb in self:
            if label == bb.label_in:
                return bb
        raise CFGException("Couldn't find block with the right label")

    def get_heads(self):
        return self.heads_labels.copy()

    def find_pred(self, label: 'Symbol') -> set['BasicBlock']:
        """
        Returns a set of basic blocks such that for each of them
        label is in their `.get_followers_labels`
        :param label:
        :return:
        """
        s = set()
        i: 'BasicBlock'
        for i in self:
            if label in i.get_follower_labels():
                s.add(i)
        return s

    def liveness(self):
        bb: 'BasicBlock'
        while any(map(lambda bb: bb.liveness_iter(), self)):
            pass

        for bb in self:
            bb.instr_liveness()

    def __iter__(self):
        return CFGIter(self)

class CFGIter:
    def __init__(self, cfg: CFG):
        self.queue: list['BasicBlock'] = []
        for _, b in cfg.functions.items():
            b: 'LoweredBlock'
            self.queue.append(b.entry_bb)
        self.queue.append(cfg.global_block.entry_bb)
        self.visited = set()

    def __next__(self):
        try:
            bb = self.queue.pop()
            nxt = set(bb.successors())
            self.visited.add(bb)
            self.queue.extend(nxt - self.visited)
            return bb
        except IndexError:
            raise StopIteration()

    def __iter__(self):
        return self


if __name__ == '__main__':
    Symbol = src.Symbols.Symbols.Symbol
    BasicBlock = src.ControlFlow.BBs.BasicBlock
