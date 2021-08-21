from src.ControlFlow.BBs import BasicBlock
from src.ControlFlow.lowered import LoweredBlock, LowDefList, LoweredDef, StatList
from src.IR.symbols import Symbol


class CFG(list):
    def __init__(self, program: LoweredBlock):
        super(CFG, self).__init__()
        queue = [program]

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
                self.extend(el.to_bbs())

        bb: BasicBlock
        for bb in self:
            if lab_t := bb.target_lab:
                bb.add_succs(alt=self.find_by_lab(lab_t))
            bb.remove_useless_next()

    def find_by_lab(self, label: Symbol) -> BasicBlock:
        pass