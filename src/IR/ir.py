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
        self.lowered: lwr.LoweredStat = None #TODO: in the lowering function, add a reference to the
                                             # lowered in this variable
        self.children = []
        c: IRNode
        if children is None:
            children = []
        for c in children:
            self.children.append(c)
            c.parent = self
        self.symtab = symtab

    def children_nodes(self) -> tuple[set[str], set[str]]:
        """
        This function is supposed to be extended by the user to notify
        which attributes represent children nodes/lists of children nodes

        All attributes / the elements of the lists must support the `navigate`
        method

        :return: A tuple where the first element is a list of attributes
            containing a single node and the second is a list of attributes
            containing a list of nodes
        """
        return set(), {"children"}

    def navigate(self, action, inplace=False, *args, **kwargs):
        """
        :param action: The action to be run, first argument always the object,
            followed by provided arguments
        :param inplace: If true then the attributes are replaces with
            the result of navigate on them
        :param args: positional arguments to pass to the function
        :param kwargs: keyword arguments to pass to the function
        :return: the result of the action applied to self
        """
        attrs, lists = self.children_nodes()

        for i in attrs:
            val = self.__getattribute__(i)
            try:
                r = val.navigate(action, inplace, *args, **kwargs)
                if inplace:
                    self.__setattr__(i, r)
            except Exception:
                pass # Can't navigate this node

        for i in lists:
            val = self.__getattribute__(i)
            r = []
            for el in val:
                try:
                    res = el.navigate(action, inplace, *args, **kwargs)
                    r.append(res)
                except Exception:
                    r.append(el) # can't navigate this node

            if inplace:
                self.__setattr__(i, r)

        return action(self, *args, **kwargs)

    @abc.abstractmethod
    def lower(self) -> lwr.LoweredStat:
        """
        This function assumes that all children nodes are
        already lowered and returns the lowered version of the
        Node
        :return:
        """
        pass


class Block(IRNode):
    """
    A block with a local symbol table, references to the global
    symbol table and to the definition list
    """
    def __init__(self, parent=None,
                 glob: SymbolTable=None,
                 local: SymbolTable=None,
                 defs: 'DefinitionList'=None,
                 body: IRNode=None,
                 top_level=False):
        super(Block, self).__init__(parent, [], local)
        self.top_level = top_level
        self.glob = glob
        self.local = local
        self.body = body
        self.defs: DefinitionList = defs
        self.body.parent = self
        self.defs.parent = self

    def children_nodes(self) -> tuple[set[str], set[str]]:
        attrs, lsts = super().children_nodes()
        return attrs.union(["body", "defs", "glob", "local"]), lsts


class Placebo(IRNode):
    """
    To be returned when no node was created in the parsing
    """


class Definition(IRNode):
    def __init__(self, parent=None, symbol=None):
        super(Definition, self).__init__()
        self.parent = parent
        self.symbol = symbol

    def children_nodes(self) -> tuple[set[str], set[str]]:
        attrs, lsts = super().children_nodes()
        return attrs.union(['symbol']), lsts


class FunctionDef(Definition):
    def __init__(self, symbol=None, body=None):
        super(FunctionDef, self).__init__(symbol=symbol)
        self.body = body
        self.body.parent = self

    def get_global_symbols(self):
        return self.body.glob.exclude([TYPENAMES['function'], TYPENAMES['label']])

    def children_nodes(self) -> tuple[set[str], set[str]]:
        attrs, lsts = super().children_nodes()
        return attrs.union(['body']), lsts


class DefinitionList(IRNode):
    def append(self, el):
        el.parent = self
        self.children.append(el)


# Expressions

class Expression(IRNode):
    """

    """
    pass


class BinExpr(Expression):
    """

    """
    def __init__(self, op, parent=None, operands=None, symtab=None):
        super(BinExpr, self).__init__(parent, operands, symtab)
        if len(operands)!=2:
            raise IRException("Error in initializing a BinExpr with: ", operands)
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
                           srcb=src_b)

        statl = [self.children[0].lowered,
                 self.children[1].lowered,
                 stmt]
        return lwr.StatList(children=statl, symtab=self.symtab)


class UnExpr(Expression):
    def __init__(self, op, parent=None, trgt=None, symtab=None):
        super(UnExpr, self).__init__(parent, [trgt], symtab)
        if len(self.children)!=1:
            raise IRException("Error in initializing a UnExpr with: ", self.children)
        self.op=op

    def lower(self) -> lwr.LoweredStat:
        src = self.children[0].lowered.destination()
        dest = new_temporary(self.symtab, src.stype)
        stmt = lwr.UnaryStat(dest=dest, op=self.op, src=src, symtab=self.symtab)
        statl = [self.children[0].lowered, stmt]
        return lwr.StatList()


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

    def lower(self) -> lwr.LoweredStat:
        pass

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