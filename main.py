import src
import src.lexer as lexer
import src.parser as parser
from src.Allocator.Regalloc import LinearScanRegAlloc
from src.Codegen.Code import Code
from src.ControlFlow.BBs import BasicBlock
from src.ControlFlow.CodeContainers import LoweredBlock

prog_1 = '''VAR x, y, squ;
VAR arr[5]: char;
var multid[5][5]: short;

{This is a comment. You can write anything you want in a comment}

PROCEDURE square;
VAR test;
BEGIN
   test := 1234;
   squ := x * x
END;

BEGIN
   x := -1;

   read x;
   if x > 100 then begin
      print -x
   end else begin
      print x
   end;

   x := 1;
   WHILE x <= 10 DO
   BEGIN
      CALL square;
      x:=x+1;
      !squ
   END;

   x := 101;
   while x <= 105 do begin
    arr[x-100] := x;
    !arr[x-100];
    x := x + 1
   end;

   x := 1;
   y := 1;
   while x <= 5 do begin
    while y <= 5 do begin
      multid[x][y] := arr[x];
      !multid[x][y];
      x := x + 1;
      y := y + 1
    end
  end
END.'''

prog_2_simple_fun = """VAR x, squ;
PROCEDURE square;
    VAR ysquare;
    PROCEDURE nested;
        VAR nesvar;
        BEGIN
            ysquare := 10
        END;
    BEGIN
        x := 1
    END;

BEGIN
   CALL square;
   squ:=2
END. 
"""

prog_3_nested = """VAR x;
PROCEDURE lev0_a;
    VAR y;
    PROCEDURE lev1_a;
        VAR z;
        BEGIN
            z:=1;
            CALL lev0_b
        END;
    BEGIN
        call lev1_a
    END;
PROCEDURE lev0_b;
    VAR w;
    BEGIN
        w:=2
    END;
BEGIN
    call lev0_a;
    x:=0
END."""

test_program = prog_1
lex = lexer.Lexer(test_program)
prog = parser.Program(lex).parse()

def lower_func(obj, log, errs):
    if not isinstance(obj, src.IR.IR.IRNode):
        errs.append(obj)
        return None
    low = obj.lower()
    log.append((obj, low))
    return low


log = []
errs = []

prog.mxdt_navigate(lower_func, log, errs)
prog = prog.lowered
prog: LoweredBlock

prog.perform_data_layout()

import src.ControlFlow.CFG as CFG

def iter_bbs_in_fun(entry, instr=False):
    entry: 'BasicBlock'
    queue = [entry]
    visited = set()
    while len(queue) > 0:
        while True:
            bb = queue.pop(0) # first in first out should guarantee breadth first
            if bb not in visited:
                break
        visited.add(bb)
        queue.extend(set(bb.successors()) - visited)
        if instr:
            for ins in bb.statements:
                yield bb, ins
        else:
            yield bb

def iter_cfg(cfg, instr=False):
    cfg: 'CFG'
    funcs: list['LoweredBlock'] = [cfg.global_block] + list(cfg.functions.values())
    funcs: list['BasicBlock'] = [i.entry_bb for i in funcs if i.entry_bb]
    for entry_bb in funcs:
        for el in iter_bbs_in_fun(entry_bb, instr):
            yield el

cfg = CFG.CFG(prog)
cfg.liveness()
#lsa = LinearScanRegAlloc(11, CFG.CFGIter)
lsa = LinearScanRegAlloc(6, iter_cfg)
allocator = lsa(cfg)

code = Code()
layout = cfg.global_block.prepare_layout(allocinfo=allocator)
ret = cfg.global_block.emit_code(code, layout=layout, regalloc=allocator)

print('\n'.join(code.lines))

entry_glob = cfg.global_block.entry_bb
if __name__ == '__main__':
    pass
