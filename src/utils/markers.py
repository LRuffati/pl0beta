import abc
from typing import Optional as Opt

import src


class Codegen(abc.ABC):

    # TODO: @abc.abstractmethod
    def emit_code(self, code: 'Code', *,
                  layout: 'StackLayout' = None,
                  symtab: 'SymbolTable' = None,
                  regalloc: 'AllocInfo' = None,
                  bblock: 'BasicBlock' = None,
                  container: 'LoweredBlock' = None) -> Opt['Code']:
        pass

    def prepare_layout(self, *,
                       layout: 'StackLayout' = None,
                       symtab: 'SymbolTable' = None,
                       regalloc: 'AllocInfo' = None,
                       bblock: 'BasicBlock' = None,
                       container: 'LoweredBlock' = None) -> Opt['StackLayout']:
        pass


class Lowered(Codegen):
    def set_label(self, label):
        raise NotImplementedError()

    def destination(self):
        raise NotImplementedError()


if __name__ == '__main__':
    Code = src.Codegen.Code
    StackLayout = src.Codegen.FrameUtils.StackLayout
    SymbolTable = src.Symbols.Symbols.SymbolTable
    AllocInfo = src.Allocator.Regalloc.AllocInfo
    BasicBlock = src.ControlFlow.BBs.BasicBlock
    LoweredBlock = src.ControlFlow.CodeContainers.LoweredBlock
