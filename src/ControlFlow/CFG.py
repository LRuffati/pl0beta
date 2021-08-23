from src.ControlFlow.BBs import BasicBlock
from src.Codegen.lowered import LoweredBlock, StatList
from src.IR.symbols import Symbol
from src.utils.exceptions import CFGException


class CFG(list):
    def __init__(self, program: LoweredBlock):
        super(CFG, self).__init__()
        queue = [program]
        glob_stat_lst = None
        self.global_entry = None
        self.functions = {}

        while True:
            try:
                el = queue.pop()
            except IndexError:
                break

            if isinstance(el, LoweredBlock):
                queue.append(el.body)
                for i in el.defs.defs:
                    queue.append(i.body)

            if isinstance(el, StatList):
                bbs = el.to_bbs()
                if (fun := el.function) is None:
                    self.global_entry = bbs[0].label_in
                else:
                    self.functions[fun] = bbs[0].label_in
                self.extend(bbs)

        blocks_labs: set[Symbol] = set()
        follows_labs: set[Symbol] = set()

        bb: BasicBlock
        for bb in self:
            blocks_labs.add(bb.label_in)
            follows_labs |= bb.get_follower_labels()

            if lab_t := bb.target_lab:
                bb.add_succs(alt=self.find_by_lab(lab_t))
            bb.remove_useless_next()

        self.heads_labels = blocks_labs - follows_labs

    def find_by_lab(self, label: Symbol) -> BasicBlock:
        bb: BasicBlock
        for bb in self:
            if label == bb.label_in:
                return bb
        raise CFGException("Couldn't find block with the right label")

    def get_heads(self):
        return self.heads_labels.copy()

    def find_pred(self, label: Symbol) -> set[BasicBlock]:
        """
        Returns a set of basic blocks such that for each of them
        label is in their `.get_followers_labels`
        :param label:
        :return:
        """
        s = set()
        i: BasicBlock
        for i in self:
            if label in i.get_follower_labels():
                s.add(i)
        return s

    def liveness(self):
        bb: BasicBlock
        while any(map(lambda bb: bb.liveness_iter(), self)):
            pass

        for bb in self:
            bb.instr_liveness()