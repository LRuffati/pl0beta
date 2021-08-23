"""
Executed after the lowering phase to associate all variables and their respective
data information
"""
import src.Codegen.lowered as lwr
import src.ControlFlow.CodeContainers as ctnrs


class SymbolLayout:
    def __init__(self, symname, bsize):
        self.symname = symname
        self.bsize = bsize


class LocalSymbolLayout(SymbolLayout):
    def __init__(self, symname, reloff, bsize, level):
        """

        :param symname: Symbol name
        :param reloff: Offset of the variable relative to
                        the base of the local variables on the stack
        :param bsize: Size
        :param level: The level of the function, allows for nested
                     functions to access the variables of parents
        """
        super().__init__(symname, bsize)
        self.reloff = reloff
        self.level = level

    def __repr__(self):
        return f"{self.symname} + : ... + ({repr(self.reloff)}) " \
               f"[def byte {repr(self.bsize)}]"


class GlobalSymbolLayout(SymbolLayout):
    def __init__(self, symname, bsize):
        super(GlobalSymbolLayout, self).__init__(symname, bsize)

    def __repr__(self):
        return f"{self.symname}: def byte {repr(self.bsize)}"


class DataLayout:
    @staticmethod
    def perform_program_layout(root: 'ctnrs.LoweredBlock'):
        root.perform_data_layout()