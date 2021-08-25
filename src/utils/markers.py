import abc

import src


class Codegen(abc.ABC):

    # TODO: @abc.abstractmethod
    def emit_code(self, *,
                  layout: 'StackLayout' = None,
                  symtab: 'SymbolTable' = None,
                  regalloc: 'AllocInfo') -> 'Code':
        pass

    def prepare_layout(self, *,
                       layout: 'StackLayout',
                       symtab: 'SymbolTable',
                       regalloc: 'AllocInfo'):
        return layout


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