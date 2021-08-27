from typing import Optional as Opt

import src
from src.Codegen.FrameUtils import FrozenLayout, StackLayout, StackSection
from src.Codegen.Lowered import EmptyStat
from src.Codegen.codegenUtils import save_registers, restore_regs
from src.ControlFlow.BBs import BasicBlock, FakeBlock
from src.ControlFlow.DataLayout import DataLayout, GlobalSymbolLayout, LocalSymbolLayout
from src.utils.Exceptions import IRException
from src.utils.markers import Lowered
import src.Codegen.registers as R


class LoweredBlock(Lowered, DataLayout):
    def set_label(self, label):
        raise IRException("Trying to set a label to a block")

    def destination(self):
        raise IRException("Trying to get destination register of a block")

    def __init__(self, *, symtab, function, body, defs):
        self.symtab: 'SymbolTable' = symtab
        self.function: Opt['Symbol'] = function  # if None then it's global
        self.statlist: 'StatList' = body
        self.defs: 'LowDefList' = defs
        # ^ Info from lowering

        self.statlist.bind_to_func(self.function)
        # ^ Actions

        self.entry_bb: Opt['FakeBlock'] = None
        self.exit_bb: Opt['FakeBlock'] = None

    def perform_data_layout(self):
        """
        Perform layout of the local variables (and possibly args), assign global if
        self.function is None

        Then perform the data layout of all defined functions
        :return: None
        """
        if self.function is None:
            prefix = "_g_"

            var: 'Symbol'
            for var in self.symtab:
                if var.stype.size == 0:
                    continue
                var.set_alloc_info(GlobalSymbolLayout(prefix + var.name, var.stype.size // 8))
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

    def to_bbs(self) -> list['BasicBlock']:
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
        self.entry_bb = FakeBlock(self.function, self.symtab, folls=entry_bbs)
        self.entry_bb.bind_to_block(self)

        self.exit_bb = FakeBlock(self.function, self.symtab, preds=exit_bbs)
        self.exit_bb.bind_to_block(self)

        self.statlist = None  # from now on only use basic blocks as a way to access
        # instructions, this allows modifying the instructions from the CFG view

        return [self.entry_bb] + lst + [self.exit_bb]

    def prepare_layout(self, *, layout: Opt['StackLayout'] = None,
                       allocinfo: 'AllocInfo' = None, **othr) -> 'StackLayout':
        """
        Receives the layout of the parent, turns it into a frozen layout,
        creates a new layout and populates it by iterating over the instructions
        """
        if self.function is None:
            # I'm the global block
            prev = None
        else:
            prev = FrozenLayout(layout, ['args_in', 'local_vars'])
        new = StackLayout(prev)

        levels_above = StackSection('level_ref')
        if self.function is None:  # if the block is the global block
            levels_above.set_size(0)
        else:
            levels_above.set_size(self.function.level)
        new.add_section(levels_above, True)

        new.add_section(StackSection('args_in'), True)

        reg_save_in = StackSection('regsave_in', False)
        reg_save_in.set_size(len(self.get_regs_save()))
        new.add_section(reg_save_in)

        local_vars = StackSection('local_vars')
        if self.function is not None:
            for sym in self.symtab:
                local_vars.grow(symb=sym)
        new.add_section(local_vars)

        spll = StackSection('spill')
        new.add_section(spll)

        new.add_section(StackSection('regsave_out'))
        new.add_section(StackSection('args_out'))

        for bb, instr in BasicBlock.iter_bbs(self.entry_bb, instr=True):
            instr: 'LoweredStat'
            instr.prepare_layout(layout=new, symtab=self.symtab, regalloc=allocinfo, bblock=bb, container=self)

        return new

    def get_regs_save(self):
        return [4, 5, 6, 7, 8, 9, 10, R.FP, R.LR]

    def emit_code(self, code: 'Code', *,
                  layout: 'StackLayout' = None,
                  regalloc: 'AllocInfo' = None,
                  **other) -> Opt['Code']:
        code_for_later: list['Code'] = []

        # If global prepare global variables
        if self.function is None:
            for sym in self.symtab:
                sym: 'Symbol'
                if sym.allocinfo:
                    code.global_var(sym.name, sym.allocinfo.bsize)
            code.set_ident(1)
            code.new_line()

        # Add the code for all defined functions before generating any code
        for defun in self.defs.lst:
            block_fun = defun.body
            layout_child = block_fun.prepare_layout(layout=layout,
                                                    allocinfo=regalloc)
            code_for_later.append(block_fun.emit_code(code,
                                                      layout=layout_child,
                                                      regalloc=regalloc))

        # From here I'm generating the actual block code
        if self.function:
            code.comment(f"Block for {self.function}")
            code.label(self.function.name)
        else:
            code.comment("Global block")
            code.instruction('.global __pl0_start')
            code.label('__pl0_start')

        code.instruction(f'mov {R.FP}, {R.SP}')
        code.instruction(f'sub {R.SP}, {R.SP}, #{layout.frame_size()*4}')

        save_registers(*self.get_regs_save(),
                       section='regsave_in',
                       code=code,
                       layout=layout,
                       regalloc=regalloc)

        later_code_instr: list['Code'] = []
        for bb, instr in BasicBlock.iter_bbs(self.entry_bb, instr=True):
            instr: 'LoweredStat'
            bb: 'BasicBlock'
            try:
                if not isinstance(instr, EmptyStat):
                    code.comment(repr(instr))
                later_code_instr.append(instr.emit_code(code,
                                                    layout=layout,
                                                    symtab=self.symtab,
                                                    regalloc=regalloc,
                                                    bblock=bb,
                                                    container=self))
            except:
                # TODO: temporary to avoid exceptions
                pass

        code.instruction(f'mov sp, fp')
        restore_regs(*self.get_regs_save(),
                     section='regsave_in',
                     code=code,
                     layout=layout,
                     regalloc=regalloc)
        code.instruction(f'bx lr')  # Return to function

        # TODO: do something with the two lists if needed
        code.new_line()
        return None


class LoweredDef(Lowered, DataLayout):
    def set_label(self, label):
        raise IRException("Trying to set label of definition")

    def destination(self):
        raise IRException("Trying to get destination of function definition")

    def __init__(self, *, body, func: 'Symbol'):
        super(LoweredDef, self).__init__()
        self.body: LoweredBlock = body
        self.function: 'Symbol' = func

    def perform_data_layout(self):
        self.body.perform_data_layout()


class LowDefList(Lowered):
    def set_label(self, label):
        raise IRException("Trying to set label to definition list")

    def destination(self):
        raise IRException("Trying to get destination of definition list")

    def __init__(self, *, children):
        self.lst: list[LoweredDef] = children


if __name__ == '__main__':
    Symbol = src.Symbols.Symbols.Symbol
    SymbolTable = src.Symbols.Symbols.SymbolTable
    LoweredStat = src.Codegen.Lowered.LoweredStat
    StatList = src.Codegen.Lowered.StatList
    AllocInfo = src.Allocator.Regalloc.AllocInfo
    Code = src.Codegen.Code.Code
