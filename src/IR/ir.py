import abc

from src.IR.irUtils import *
from symbols import *
import src.ControlFlow.lowered as lwr
from src.utils.exceptions import IRException

class IRNode(abc.ABC):
    """
    IRNodes have a parent and zero or more children
    They can be lowered to lowered statements that are
    then converted into code
    """
    def __init__(self, parent: 'IRNode' = None,
                 children: list['IRNode'] = None,
                 symtab: SymbolTable = None):
        self.parent = parent
        self.children = []
        c: IRNode
        if children is None:
            children = []
        for c in children:
            self.children.append(c)
            c.parent = self
        self.symtab = symtab

    @abc.abstractmethod
    def lower(self) -> lwr.LoweredStat:
        pass


class Block(IRNode):
    """
    A block with a local symbol table, references to the global
    symbol table and to the definition list
    """
    def __init__(self, parent=None,
                 glob: SymbolTable=None,
                 local: SymbolTable=None,
                 defs: DefinitionList=None,
                 body: IRNode=None):
        super(Block, self).__init__(parent, [], local)
        self.glob = glob
        self.local = local
        self.body = body
        self.defs: DefinitionList = defs
        self.body.parent = self
        self.defs.parent = self


class Placebo(IRNode):
    """
    To be returned when no node was created in the parsing
    """


class Definition(IRNode):
    def __init__(self, parent=None, symbol=None):
        super(Definition, self).__init__()
        self.parent = parent
        self.symbol = symbol

class FunctionDef(Definition):
    def __init__(self, symbol=None, body=None):
        super(FunctionDef, self).__init__(symbol=symbol)
        self.body = body
        self.body.parent = self

    def get_global_symbols(self):
        return self.body.glob.exclude([TYPENAMES['function'], TYPENAMES['label']])

# Expressions

class Expression(IRNode):
    """

    """
    pass


class BinExpr(Expression):
    """

    """
    def __init__(self, parent=None, children=None, symtab=None):
        super(BinExpr, self).__init__(parent, children, symtab)
        if len(children)!=3:
            raise IRException("Error in initializing a BinExpr with: ", children)

    def get_operands(self):
        return self.children[1:]


class UnExpr(Expression):
    def __init__(self, parent=None, children=None, symtab=None):
        super(UnExpr, self).__init__(parent, children, symtab)
        if len(children)!=2:
            raise IRException("Error in initializing a UnExpr with: ", children)


class CallExpr(Expression):
    def __init__(self, parent=None, function=None, symtab=None, parameters=None):
        super(CallExpr, self).__init__(parent, [], symtab)
        self.symbol = function
        if parameters:
            self.children = parameters[:]


# Variables

class Const(IRNode):
    """
    """
    def __init__(self, parent=None, value=None, symtab=None, symb=None):
        super(Const, self).__init__(parent, None, symtab)
        self.value = value
        self.symbol = symb


class ArrayElement(IRNode):
    """
    Loads in a temporary register the value pointed at by the
    symbol at the given offset
    """
    def __init__(self, parent=None, var=None, offset=None, symtab=None):
        """
        Offset must be a single expression, multi dimensional arrays
        have to be flattened
        :param var:
        :param offset:
        :param symtab:
        """
        super(ArrayElement, self).__init__(parent,[offset],symtab)
        self.symbol = var
        self.offset = offset


class Var(IRNode):
    """
    Loads in a temporary register the value pointed at by the symbol
    """
    def __init__(self, parent=None, var=None, symtab=None):
        super(Var, self).__init__(parent, None, symtab)
        self.symbol = var


# Statements

class Statement(IRNode):
    def __init__(self, parent=None, children=None, symtab=None):
        super(Statement, self).__init__(parent, children, symtab)
        self.label = None

    def set_label(self, label: LabelType):
        self.label = label
        label.value = self

    def get_label(self) -> LabelType:
        return self.label


class AssignStat(Statement):
    def __init__(self, parent=None, 
                 target=None, offset=None, 
                 expression=None, symtab=None):
        super(AssignStat, self).__init__(parent, [], symtab)
        self.symbol = target
        try:
            self.symbol.parent = self
        except AttributeError:
            pass

        self.expr = expression
        self.expr.parent = self
        self.offset = offset
        if self.offset is not None:
            self.offset.parent = self



class CallStat(Statement):
    def __init__(self, parent=None, call_expr: CallExpr =None, symtab=None):
        super(CallStat, self).__init__(parent, [], symtab)
        self.call = call_expr
        self.call.parent = self


class StatList(Statement):
    def __init__(self, parent=None, children=None, symtab=None):
        super(StatList, self).__init__(parent, children, symtab)

    def append(self, statement):
        self.children.append(statement)


class IfStat(Statement):
    def __init__(self, parent=None,
                 cond=None, then=None, els=None, symtab=None):
        super(IfStat, self).__init__(parent,[],symtab)
        self.cond = cond
        self.then = then
        self.elsep = els
        self.cond.parent = self
        self.then.parent = self
        if self.elsep:
            self.elsep.parent = self


class WhileStat(Statement):
    def __init__(self, parent=None, cond=None, body=None, symtab=None):
        super(WhileStat, self).__init__(parent, [], symtab)
        self.cond = cond
        self.body = body
        self.cond.parent = self
        self.body.parent = self


class PrintStat(Statement):
    def __init__(self, parent=None, exp=None, symtab=None):
        super(PrintStat, self).__init__(parent, [exp], symtab)
        self.expr = exp


class ReadStat(Statement):
    def __init__(self, symtab=None):
        pass