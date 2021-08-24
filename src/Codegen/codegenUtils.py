import abc

from src.Codegen.FrameUtils import StackLayout
from src.IR.symbols import SymbolTable


class Codegen(abc.ABC):

    # TODO: @abc.abstractmethod
    def emit_code(self,
                  layout: StackLayout = None,
                  symtab: SymbolTable = None) -> 'Code':
        pass


class Lowered(Codegen):
    def set_label(self, label):
        raise NotImplementedError()

    def destination(self):
        raise NotImplementedError()


class Code:
    pass
