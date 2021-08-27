import abc
from abc import ABC
from functools import reduce

import src.lexer as lexer
from src.utils.Logger import Logged
from src.utils.Exceptions import *
import src.IR.IR
from src.IR.IR import IRNode
from src.Symbols.Symbols import Symbol, SymbolTable, ArrayType, TYPENAMES

ir = src.IR.IR


class Parser(Logged, ABC):
    def __init__(self, lxr: lexer.Lexer):
        if type(lxr) is src.lexer.LexerIter:
            self.lxr = lxr
        else:
            self.lxr: src.lexer.LexerIter = iter(lxr)

    @classmethod
    def create_parser(cls, lexer):
        return cls(lexer)

    def parse_item(self, cls_to_parse, *args, **kwargs):
        if not isinstance(cls_to_parse, type):
            raise ParseException("Must receive the class, not an instance")
        if not issubclass(cls_to_parse, Parser):
            raise ParseException("The class must be an instance of Parser")
        parse_el = cls_to_parse.create_parser(self.lxr)
        return parse_el.parse(*args, **kwargs)

    @abc.abstractmethod
    def parse(self, *args, **kwargs) -> IRNode:
        pass


class ArrayUtils(Parser, ABC):
    def array_offset(self, symtab: SymbolTable, target):
        offset = None
        target: Symbol = symtab.lookup(target)
        if isinstance(target.stype, ArrayType):
            idxs = []
            for i in range(0, len(target.stype.dims)):
                self.lxr.expect('lspar')
                idxs.append(self.parse_item(Expression, symtab))
                self.lxr.expect('rspar')
            offset = self.linearize_multid_vector(idxs, target, symtab)
        return offset

    @staticmethod
    def linearize_multid_vector(idxs, target: 'Symbol', symtab):
        offset = None
        for i in range(0, len(target.stype.dims)):
            if i + 1 < len(target.stype.dims):
                planedisp = reduce(lambda x, y: x * y, target.stype.dims[i + 1:])
            else:
                planedisp = 1
            idx = idxs[i]
            esize = (target.stype.basetype.size // 8) * planedisp
            planed = ir.BinExpr(op='times',
                                operands=[idx, ir.Const(value=esize, symtab=symtab)],
                                symtab=symtab)
            if offset is None:
                offset = planed
            else:
                offset = ir.BinExpr(op='plus',
                                    operands=[offset, planed],
                                    symtab=symtab)
        return offset


class Program(Parser):
    def parse(self, *args, **kwargs) -> IRNode:
        global_symtab = SymbolTable()
        prog = self.parse_item(Block, symtab=global_symtab)
        self.lxr.expect('period')
        return prog


class Block(Parser):
    def parse(self, *args, symtab: SymbolTable,
              alloct='auto', function=None, **kwargs) -> IRNode:
        if function is None:
            local = symtab  # if the block is the global block I need to use the global
            # table
        else:
            local = symtab.create_local()
        defs = ir.DefinitionList()

        while True:
            if self.lxr.accept('constsym'):
                self.parse_item(ConstDef, symtab=local, alloct=alloct)
            elif self.lxr.accept('varsym'):
                self.parse_item(VarDef, symtab=local, alloct=alloct)
                while self.lxr.accept('comma'):
                    self.parse_item(VarDef, symtab=local, alloct=alloct)
            else:
                break
            self.lxr.expect('semicolon')

        while self.lxr.accept('procsym'):
            func = self.parse_item(FuncDef, symtab=local)
            defs.append(func)

        stat = self.parse_item(Statement, local)
        return ir.Block(symtab=local, defs=defs, body=stat, function=function)


class ConstDef(Parser):
    def parse(self, *args, symtab, alloct='auto', **kwargs) -> IRNode:
        while True:
            _, name = self.lxr.expect('ident')
            self.lxr.expect('eql')
            _, val = self.lxr.expect('number')
            symtab.append(Symbol(name,
                                 TYPENAMES['int'],
                                 alloct=alloct),
                          int(val))
            if not self.lxr.accept('comma'):
                break
        return src.IR.IR.Placebo()


class VarDef(Parser):
    def parse(self, *args, symtab, alloct='auto', **kwargs) -> IRNode:
        _, name = self.lxr.expect('ident')
        size = []
        while self.lxr.accept('lspar'):
            _, n = self.lxr.expect('number')
            size.append(int(n))
            self.lxr.expect('rspar')

        typ = TYPENAMES['int']
        if self.lxr.accept('colon'):
            _, typ = self.lxr.accept('ident')
            typ = TYPENAMES[typ]

        if len(size) > 0:
            symtab.append(Symbol(name, ArrayType(None, size, typ), alloct=alloct))
        else:
            symtab.append(Symbol(name, typ, alloct=alloct))

        return src.IR.IR.Placebo()


class FuncDef(Parser):
    def parse(self, *args, symtab: SymbolTable, **kwargs) -> IRNode:
        _, fname = self.lxr.expect('ident')
        self.lxr.expect('semicolon')
        fsym = Symbol(fname, TYPENAMES['function'])
        symtab.append(fsym)

        fbody = self.parse_item(Block, symtab=symtab, function=fsym)
        self.lxr.expect('semicolon')
        return ir.FunctionDef(symbol=symtab.lookup(fname), body=fbody)


class Statement(Parser):
    def parse(self, symtab, *args, **kwargs) -> IRNode:
        if self.lxr.preview('ident'):
            return self.parse_item(Assignment, symtab)
        elif self.lxr.preview('callsym'):
            return self.parse_item(FuncCall, symtab)
        elif self.lxr.preview('beginsym'):
            return self.parse_item(StatList, symtab)
        elif self.lxr.preview('ifsym'):
            return self.parse_item(IfStat, symtab)
        elif self.lxr.preview('whilesym'):
            return self.parse_item(WhileStat, symtab)
        elif self.lxr.preview('print'):
            return self.parse_item(Print, symtab)
        elif self.lxr.preview('read'):
            return self.parse_item(Read, symtab)
        else:
            raise ParseException("Can't parse Statement")


class Assignment(Statement, ArrayUtils):
    def parse(self, symtab: SymbolTable, *args, **kwargs) -> IRNode:
        _, targ = self.lxr.expect('ident')
        offset = self.array_offset(symtab, targ)
        self.lxr.expect('becomes')
        expr = self.parse_item(Expression, symtab)
        targ = symtab.lookup(targ)
        return src.IR.IR.AssignStat(target=targ,
                                    offset=offset,
                                    expression=expr,
                                    symtab=symtab)


class FuncCall(Statement):
    def parse(self, symtab: SymbolTable, *args, **kwargs) -> IRNode:
        self.lxr.expect('callsym')
        _, fun = self.lxr.expect('ident')
        return ir.CallStat(call_expr=ir.CallExpr(function=fun,
                                                 symtab=symtab),
                           symtab=symtab)


class StatList(Statement):
    def parse(self, symtab, *args, **kwargs) -> IRNode:
        self.lxr.expect('beginsym')
        stat_list = ir.StatList(symtab=symtab)

        while True:
            stat = self.parse_item(Statement, symtab)
            stat_list.append(stat)
            if not self.lxr.accept('semicolon'):
                break

        self.lxr.expect('endsym')
        return stat_list


class IfStat(Statement):
    def parse(self, symtab, *args, **kwargs) -> IRNode:
        self.lxr.expect('ifsym')
        cond = self.parse_item(Condition, symtab)
        self.lxr.expect('thensym')
        then = self.parse_item(Statement, symtab)
        els = None
        if self.lxr.accept('elsesym'):
            els = self.parse_item(Statement, symtab)

        return ir.IfStat(cond=cond, then=then, els=els, symtab=symtab)


class WhileStat(Statement):
    def parse(self, symtab, *args, **kwargs) -> IRNode:
        self.lxr.expect('whilesym')
        cond = self.parse_item(Condition, symtab)
        self.lxr.expect('dosym')
        body = self.parse_item(Statement, symtab)
        return ir.WhileStat(cond=cond, body=body, symtab=symtab)


class Print(Statement):
    def parse(self, symtab, *args, **kwargs) -> IRNode:
        self.lxr.expect('print')
        exp = self.parse_item(Expression, symtab)
        return ir.PrintStat(exp=exp, symtab=symtab)


class Read(ArrayUtils, Statement):
    def parse(self, symtab: SymbolTable, *args, **kwargs) -> IRNode:
        self.lxr.expect('read')
        _, targ = self.lxr.expect('ident')
        target = symtab.lookup(targ)
        offset = self.array_offset(symtab, targ)
        return ir.AssignStat(target=target,
                             offset=offset,
                             expression=ir.ReadStat(symtab=symtab),
                             symtab=symtab)


class Expression(Parser):
    def parse(self, symtab, *args, **kwargs) -> IRNode:
        op = None
        if tup := self.lxr.accept('plus', 'minus'):
            op, _ = tup

        expr = self.parse_item(Term, symtab)
        if op:
            expr = ir.UnExpr(op=op, trgt=expr, symtab=symtab)
        while tup := self.lxr.accept('plus', 'minus'):
            op, _ = tup
            expr2 = self.parse_item(Term, symtab)
            expr = ir.BinExpr(op=op, operands=[expr, expr2], symtab=symtab)

        return expr


class Term(Parser):
    def parse(self, symtab, *args, **kwargs) -> IRNode:
        expr = self.parse_item(Factor, symtab)
        while tup := self.lxr.accept('times', 'slash'):
            op, _ = tup
            expr2 = self.parse_item(Factor, symtab)
            expr = ir.BinExpr(op=op, operands=[expr, expr2], symtab=symtab)
        return expr


class Condition(Parser):
    def parse(self, symtab, *args, **kwargs) -> IRNode:
        if self.lxr.accept('oddsym'):
            return ir.UnExpr(op='odd',
                             trgt=self.parse_item(Expression, symtab),
                             symtab=symtab)
        else:
            expr = self.parse_item(Expression, symtab)
            if tup := self.lxr.accept('eql', 'neq', 'lss', 'leq', 'gtr', 'geq'):
                op, _ = tup
                self.log("Condition operator: ", op)
                expr2 = self.parse_item(Expression, symtab)
                return ir.BinExpr(op=op, operands=[expr, expr2], symtab=symtab)
            else:
                raise ParseException("Invalid operator for condition")


class Factor(ArrayUtils, Parser):
    def parse(self, symtab, *args, **kwargs) -> IRNode:
        if tup := self.lxr.accept('ident'):
            _, var_n = tup
            var = symtab.lookup(var_n)
            offs = self.array_offset(symtab, var_n)
            if offs is None:
                return ir.Var(var=var, symtab=symtab)
            else:
                return ir.ArrayElement(var=var, offset=offs, symtab=symtab)
        elif tup := self.lxr.accept('number'):
            _, num = tup
            return ir.Const(value=int(num), symtab=symtab)
        elif self.lxr.accept('lparen'):
            expr = self.parse_item(Expression, symtab)
            self.lxr.expect('rparen')
            return expr
        else:
            raise ParseException("Syntax error while parsing Factor")
