import abc
from abc import ABC
from typing import Optional as Opt

from src.IR.irUtils import *
from src.IR.symbols import *
import src.ControlFlow.lowered as lwr
from src.utils.exceptions import IRException

from MixedTrees.src.MixedTrees import MixedTree as mxdT

class IRNode(mxdT, lower=["children"]):
    """
    IRNodes have a parent and zero or more children
    They can be lowered to lowered statements that are
    then converted into code
    """

    def __init__(self, parent: 'IRNode' = None,
                 children: list['IRNode'] = None,
                 symtab: SymbolTable = None):
        self.parent = parent
        self.lowered: Opt[lwr.LoweredStat] = None #TODO: in the lowering function, add a reference to the
                                                  # lowered in this variable
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
        """
        This function assumes that all children nodes are
        already lowered and returns the lowered version of the
        Node
        :return:
        """
        pass

    def __init_subclass__(cls, **kwargs):
        if 'lower' in dir(cls):
            low_old = cls.lower

            def new_low(self, *args, **kwargs):
                res = low_old(self, *args, **kwargs)
                self.lowered = res
                return res
            cls.lower = new_low

        return super().__init_subclass__(**kwargs)


class Block(IRNode, lower=['body', 'defs']):
    """
    A block with a local symbol table, references to the global
    symbol table and to the definition list
    """
    def __init__(self, parent=None,
                 symtab: SymbolTable = None,
                 defs: 'DefinitionList' = None,
                 body: IRNode = None,
                 top_level=False):
        super(Block, self).__init__(parent, [], symtab)
        self.top_level = top_level
        self.symtab = symtab
        self.body = body
        self.defs: DefinitionList = defs
        self.body.parent = self
        self.defs.parent = self

    def lower(self) -> lwr.LoweredBlock:
        return lwr.LoweredBlock(symtab=self.symtab, top_level=self.top_level,
                                body=self.body.lowered, defs=self.defs.lowered)


class Placebo(IRNode):
    """
    To be returned when no node was created in the parsing
    """
    def lower(self) -> lwr.LoweredStat:
        raise IRException("Lowering shouldn't have reached a placebo Node")


class Definition(IRNode):
    def __init__(self, parent=None, symbol=None):
        super(Definition, self).__init__()
        self.parent = parent
        self.symbol = symbol

    @abc.abstractmethod
    def lower(self) -> lwr.LoweredStat:
        pass


class FunctionDef(Definition, lower=['body']):
    def __init__(self, symbol=None, body=None):
        super(FunctionDef, self).__init__(symbol=symbol)
        self.body = body
        self.body.parent = self

    def get_global_symbols(self):
        return self.body.glob.exclude([TYPENAMES['function'], TYPENAMES['label']])

    def lower(self) -> lwr.LoweredDef:
        return lwr.LoweredDef(body=self.body.lowered, symtab=self.symtab)


class DefinitionList(IRNode):
    def append(self, el):
        el.parent = self
        self.children.append(el)

    def lower(self) -> lwr.LowDefList:
        return lwr.LowDefList(children=[i.lowered for i in self.children])


# Expressions


class Expression(IRNode, ABC):
    """

    """
    pass


class BinExpr(Expression):
    """

    """
    def __init__(self, op=None, parent=None, operands=None, symtab=None):
        super(BinExpr, self).__init__(parent, operands, symtab)
        if (len(operands) != 2) or (op is None):
            raise IRException("Error in initializing a BinExpr with: ", operands, op)
        self.op = op

    def get_operands(self):
        return self.children[:]

    def lower(self) -> lwr.LoweredStat:
        src_a = self.children[0].lowered.destination()
        src_b = self.children[1].lowered.destination()
        if ('unsigned' in src_a.stype.qual_list) and ('unsigned' in src_b.stype.qual_list):
            desttype = Type(None, max(src_a.stype.size, src_b.stype.size), 'Int', ['unsigned'])
        else:
            desttype = Type(None, max(src_a.stype.size, src_b.stype.size), 'Int')

        dest = new_temporary(self.symtab, desttype)
        stmt = lwr.BinStat(dest=dest,
                           op=self.op,
                           srca=src_a,
                           srcb=src_b,
                           symtab=self.symtab)

        statl = [self.children[0].lowered,
                 self.children[1].lowered,
                 stmt]
        return lwr.StatList(children=statl, symtab=self.symtab)


class UnExpr(Expression):
    def __init__(self, op, parent=None, trgt=None, symtab=None):
        super(UnExpr, self).__init__(parent, [trgt], symtab)
        if len(self.children) != 1:
            raise IRException("Error in initializing a UnExpr with: ", self.children)
        self.op = op

    def lower(self) -> lwr.LoweredStat:
        src = self.children[0].lowered.destination()
        dest = new_temporary(self.symtab, src.stype)
        stmt = lwr.UnaryStat(dest=dest, op=self.op, src=src, symtab=self.symtab)
        statl = [self.children[0].lowered, stmt]
        return lwr.StatList(children=statl, symtab=self.symtab)


class CallExpr(Expression):
    def __init__(self, parent=None, function=None, symtab=None, parameters=None):
        super(CallExpr, self).__init__(parent, [], symtab)
        self.symbol = function
        if parameters:
            self.children = parameters[:]

    def lower(self) -> lwr.LoweredStat:
        raise IRException("CallExpr should not be reached when trying"
                          "to lower")


# Variables

class Const(IRNode):
    """
    """
    def __init__(self, parent=None, value=None, symtab=None, symb=None):
        super(Const, self).__init__(parent, None, symtab)
        self.value = value
        self.symbol = symb

    def lower(self) -> lwr.LoweredStat:
        if self.symbol is None:
            new = new_temporary(self.symtab, TYPENAMES['int'])
            loadst = lwr.LoadImmStat(dest=new, val=self.value, symtab=self.symtab)
        else:
            new = new_temporary(self.symtab, self.symbol.stype)
            loadst = lwr.LoadStat(dest=new, symbol=self.symbol, symtab=self.symtab)
        return loadst


class ArrayElement(IRNode, lower=['offset']):
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
        super(ArrayElement, self).__init__(parent, [offset], symtab)
        self.symbol = var
        self.offset = offset

    def lower(self) -> lwr.LoweredStat:
        dest = new_temporary(self.symtab, self.symbol.stype.basetype)
        off = self.offset.lowered.destination()

        statl = [self.offset.lowered]

        ptrreg = new_temporary(self.symtab, PointerType(self.symbol.stype.basetype))
        loadptr = lwr.LoadPtrToSymb(dest=ptrreg, symbol=self.symbol, symtab=self.symtab)
        src = new_temporary(self.symtab, PointerType(self.symbol.stype.basetype))
        add = lwr.BinStat(dest=src, op='plus', srca=ptrreg, srcb=off, symtab=self.symtab)

        statl += [loadptr, add]
        statl += [lwr.LoadStat(dest=dest, symbol=src, symtab=self.symtab)]

        return lwr.StatList(children=statl, symtab=self.symtab)


class Var(IRNode):
    """
    Loads in a temporary register the value pointed at by the symbol
    """
    def __init__(self, parent=None, var=None, symtab=None):
        super(Var, self).__init__(parent, None, symtab)
        self.symbol = var

    def lower(self) -> lwr.LoweredStat:
        new = new_temporary(self.symtab, self.symbol.stype)
        loadst = lwr.LoadStat(dest=new, symbol=self.symbol, symtab=self.symtab)
        return loadst


# Statements


class Statement(IRNode, ABC):
    def __init__(self, parent=None, children=None, symtab=None):
        super(Statement, self).__init__(parent, children, symtab)
        self.label = None

    def set_label(self, label: LabelType):
        self.label = label
        label.value = self


class AssignStat(Statement, lower=['expr', 'offset']):
    def __init__(self, parent=None, 
                 target=None, offset=None, 
                 expression=None, symtab=None):
        super(AssignStat, self).__init__(parent, [], symtab)
        self.symbol: Symbol = target
        try:
            self.symbol.parent = self
        except AttributeError:
            pass

        self.expr: IRNode = expression
        self.expr.parent = self
        self.offset: Opt[IRNode] = offset
        if self.offset is not None:
            self.offset.parent = self

    def lower(self) -> lwr.LoweredStat:
        src = self.expr.lowered.destination()
        dst = self.symbol

        stats = [self.expr.lowered]

        if self.offset:
            off = self.offset.lowered.destination()
            desttype = dst.stype
            if type(desttype) is ArrayType:
                desttype = desttype.basetype

            ptrreg = new_temporary(self.symtab, PointerType(desttype))
            loadptr = lwr.LoadPtrToSymb(dest=ptrreg, symbol=dst, symtab=self.symtab)
            dst = new_temporary(self.symtab, PointerType(desttype))
            add = lwr.BinStat(dest=dst, op='plus', srca=ptrreg, srcb=off, symtab=self.symtab)

            stats += [self.offset.lowered, loadptr, add]
        stats += [lwr.StoreStat(dest=dst, symbol=src, symtab=self.symtab)]
        return lwr.StatList(children=stats, symtab=self.symtab)


class CallStat(Statement):
    def __init__(self, parent=None, call_expr: CallExpr = None, symtab=None):
        super(CallStat, self).__init__(parent, [], symtab)
        self.call: CallExpr = call_expr
        self.call.parent = self

    def lower(self) -> lwr.LoweredStat:
        dest = self.call.symbol
        return lwr.BranchStat(target=dest, symtab=self.symtab, returns=True)


class StatList(Statement):
    def __init__(self, parent=None, children=None, symtab=None):
        super(StatList, self).__init__(parent, children, symtab)

    def append(self, statement):
        self.children.append(statement)

    def lower(self) -> lwr.LoweredStat:
        return lwr.StatList(children=[i.lowered for i in self.children], symtab=self.symtab)


class IfStat(Statement, lower=['cond', 'then', 'elsep']):
    def __init__(self, parent=None,
                 cond=None, then=None, els=None, symtab=None):
        super(IfStat, self).__init__(parent, [], symtab)
        self.cond: IRNode = cond
        self.then: IRNode = then
        self.elsep: Opt[IRNode] = els
        self.cond.parent = self
        self.then.parent = self
        if self.elsep:
            self.elsep.parent = self

    def lower(self) -> lwr.LoweredStat:
        exit_lab = TYPENAMES['label']()
        exit_stat = lwr.EmptyStat(symtab=self.symtab)
        exit_stat.set_label(exit_lab)

        if self.elsep:
            then_lab = TYPENAMES['label']()
            self.then.lowered.set_label(then_lab)

            branch_to_then = lwr.BranchStat(condition=self.cond.lowered.destination(),
                                            target=then_lab,
                                            symtab=self.symtab)
            branch_to_exit = lwr.BranchStat(target=exit_lab,
                                            symtab=self.symtab)

            return lwr.StatList(children=[self.cond.lowered,
                                          branch_to_then,
                                          self.elsep.lowered,
                                          branch_to_exit,
                                          self.then.lowered,
                                          exit_stat],
                                symtab=self.symtab)
        else:
            branch_to_exit = lwr.BranchStat(condition=self.cond.lowered.destination(),
                                            target=exit_lab,
                                            symtab=self.symtab,
                                            negcond=True)
            return lwr.StatList(children=[self.cond.lowered,
                                          branch_to_exit,
                                          self.then.lowered,
                                          exit_stat],
                                symtab=self.symtab)


class WhileStat(Statement, lower=['cond', 'body']):
    def __init__(self, parent=None, cond=None, body=None, symtab=None):
        super(WhileStat, self).__init__(parent, [], symtab)
        self.cond: IRNode = cond
        self.body: IRNode = body
        self.cond.parent = self
        self.body.parent = self

    def lower(self) -> lwr.LoweredStat:
        entry_l = TYPENAMES['label']()
        exit_l = TYPENAMES['label']()
        exit_s = lwr.EmptyStat(symtab=self.symtab)
        exit_s.set_label(exit_l)
        self.cond.lowered.set_label(entry_l)
        branch = lwr.BranchStat(condition=self.cond.lowered.destination(),
                                target=exit_l,
                                symtab=self.symtab,
                                negcond=True)
        loop = lwr.BranchStat(target=entry_l, symtab=self.symtab)
        return lwr.StatList(children=[self.cond.lowered,
                                      branch,
                                      self.body.lowered,
                                      loop,
                                      exit_s],
                            symtab=self.symtab)


class PrintStat(Statement, lower=['expr']):
    def __init__(self, parent=None, exp=None, symtab=None):
        super(PrintStat, self).__init__(parent, [], symtab)
        self.expr: IRNode = exp

    def lower(self) -> lwr.LoweredStat:
        ps = lwr.PrintStat(src=self.expr.lowered.destination(), symtab=self.symtab)
        return lwr.StatList(children=[self.expr.lowered, ps], symtab=self.symtab)


class ReadStat(Statement):
    def lower(self) -> lwr.LoweredStat:
        tmp = new_temporary(self.symtab, TYPENAMES['int'])
        return lwr.ReadStat(dest=tmp, symtab=self.symtab)
