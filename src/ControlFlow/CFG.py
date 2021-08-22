from src.ControlFlow.BBs import BasicBlock
from src.ControlFlow.lowered import LoweredBlock, LowDefList, LoweredDef, StatList
from src.IR.symbols import Symbol
from src.utils.exceptions import CFGException


class CFG(list):
    def __init__(self, program: LoweredBlock):
        super(CFG, self).__init__()
        queue = [program]
        glob_stat_lst = None
        self.global_entry = None
        self.functions = {}

        stat_list_to_func = {}
        while True:
            try:
                el = queue.pop()
            except IndexError:
                break

            if isinstance(el, LoweredBlock):
                queue.append(el.body)
                if el.top_lev:
                    glob_stat_lst = el.body

                for i in el.defs.defs:
                    stat_list_to_func[i.body.body] = i.function
                    queue.append(i.body)

            if isinstance(el, StatList):
                bbs = el.to_bbs()
                if el == glob_stat_lst:
                    self.global_entry = bbs[0].label_in
                else:
                    fun = stat_list_to_func.pop(el)
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