import abc

import src.Codegen.FrameUtils


class Codegen(abc.ABC):

    # TODO: @abc.abstractmethod
    def emit_code(self,
                  layout: 'StackLayout' = None,
                  symtab: 'SymbolTable' = None) -> 'Code':
        pass

    def prepare_layout(self, layout: 'StackLayout', symtab: 'SymbolTable') -> 'StackLayout':
        return layout


class Lowered(Codegen):
    def set_label(self, label):
        raise NotImplementedError()

    def destination(self):
        raise NotImplementedError()


class Code:
    pass


StackLayout = src.Codegen.FrameUtils.StackLayout
SymbolTable = src.Symbols.Symbols.SymbolTable
