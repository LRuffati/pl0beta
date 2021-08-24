from typing import Optional as Opt

import src.Codegen as Codegen
import src.ControlFlow.BBs as BBs
from src.Codegen.CodegenUtils import Lowered
from src.ControlFlow.DataLayout import DataLayout, GlobalSymbolLayout, LocalSymbolLayout
from src.IR.Symbols import SymbolTable, Symbol
from src.utils.Exceptions import IRException


class LoweredBlock(Lowered, DataLayout):
    def set_label(self, label):
        raise IRException("Trying to set a label to a block")

    def destination(self):
        raise IRException("Trying to get destination register of a block")

    def __init__(self, *, symtab, function, body, defs):
        self.symtab: SymbolTable = symtab
        self.function: Opt[Symbol] = function  # if None then it's global
        self.statlist: Codegen.Lowered.StatList = body
        self.defs: LowDefList = defs
        # ^ Info from lowering

        self.statlist.bind_to_func(self.function)
        # ^ Actions

        self.entry_bb: Opt[BBs.FakeBlock] = None
        self.exit_bb: Opt[BBs.FakeBlock] = None

    def perform_data_layout(self):
        """
        Perform layout of the local variables (and possibly args), assign global if
        self.function is None

        Then perform the data layout of all defined functions
        :return: None
        """
        if self.function is None:
            prefix = "_g_"

            var: Symbol
            for var in self.symtab:
                if var.stype.size == 0:
                    continue
                var.set_alloc_info(GlobalSymbolLayout(prefix+var.name, var.stype.size//8))
        else:
            prefix = "_l_"
            offs = 0
            for var in self.symtab:
                if var.stype.size == 0:
                    continue
                bsize = var.stype.size // 8
                offs -= bsize
                var.set_alloc_info(LocalSymbolLayout(prefix + var.name,
                                                     offs,
                                                     bsize,
                                                     self.symtab.lvl))

        i: LoweredDef
        for i in self.defs.lst:
            i.perform_data_layout()
        return

    def to_bbs(self) -> list['BBs.BasicBlock']:
        lst = self.statlist.to_bbs(symtab=self.symtab)

        exit_bbs = []
        entry_bbs = []
        bblocks = set()
        bb_succ = set()
        for b in lst:
            b.bind_to_block(self)
            bblocks.add(b)
            folls = b.get_follower_labels()
            if len(folls) == 0:
                exit_bbs.append(b)
            else:
                bb_succ |= folls

        for b in bblocks:
            if b.label_in not in bb_succ:
                entry_bbs.append(b)
            else:
                bb_succ.discard(b.label_in)
        self.entry_bb = BBs.FakeBlock(self.function, self.symtab, folls=entry_bbs)
        self.entry_bb.bind_to_block(self)

        self.exit_bb = BBs.FakeBlock(self.function, self.symtab, preds=exit_bbs)
        self.exit_bb.bind_to_block(self)

        self.statlist = None  # from now on only use basic blocks as a way to access
        # instructions, this allows modifying the instructions from the CFG view

        return [self.entry_bb] + lst + [self.exit_bb]


class LoweredDef(Lowered, DataLayout):
    def set_label(self, label):
        raise IRException("Trying to set label of definition")

    def destination(self):
        raise IRException("Trying to get destination of function definition")

    def __init__(self, *, body, func: Symbol):
        super(LoweredDef, self).__init__()
        self.body: LoweredBlock = body
        self.function: Symbol = func

    def perform_data_layout(self):
        self.body.perform_data_layout()


class LowDefList(Lowered):
    def set_label(self, label):
        raise IRException("Trying to set label to definition list")

    def destination(self):
        raise IRException("Trying to get destination of definition list")

    def __init__(self, *, children):
        self.lst: list[LoweredDef] = children
