#!/usr/bin/env python3
from typing import Optional

from src.utils.exceptions import LexerException

"""Simple lexer for PL/0 using generators"""

# Tokens can have multiple definitions if needed
TOKEN_DEFS = {
    'lparen': ['('],
    'rparen': [')'],
    'lspar': ['['],
    'rspar': [']'],
    'colon': [':'],
    'times': ['*'],
    'slash': ['/'],
    'plus': ['+'],
    'minus': ['-'],
    'eql': ['='],
    'neq': ['!='],
    'lss': ['<'],
    'leq': ['<='],
    'gtr': ['>'],
    'geq': ['>='],
    'callsym': ['call'],
    'beginsym': ['begin'],
    'semicolon': [';'],
    'endsym': ['end'],
    'ifsym': ['if'],
    'whilesym': ['while'],
    'forsym': ['for'],
    'stepsym': ['by'],
    'forendsym': ['to'],
    'becomes': [':='],
    'thensym': ['then'],
    'elsesym': ['else'],
    'dosym': ['do'],
    'constsym': ['const'],
    'comma': [','],
    'varsym': ['var'],
    'procsym': ['procedure'],
    'period': ['.'],
    'oddsym': ['odd'],
    'print': ['!', 'print'],
    'read': ['?', 'read']
}


class Lexer:
    """The lexer. Decomposes a string in tokens."""

    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.str_to_token = list([(s, t) for t, ss in TOKEN_DEFS.items() for s in ss])
        self.str_to_token.sort(key=lambda a: -len(a[0]))

    def skip_whitespace(self):
        in_comment = False
        while self.pos < len(self.text) and (self.text[self.pos].isspace() or self.text[self.pos] == '{' or in_comment):
            if self.text[self.pos] == '{' and not in_comment:
                in_comment = True
            elif in_comment and self.text[self.pos] == '}':
                in_comment = False
            self.pos += 1

    def check_symbol(self):
        for s, t in self.str_to_token:
            if self.text[self.pos:self.pos + len(s)].lower() == s:
                self.pos += len(s)
                return t, s
        return None, None

    def check_regex(self, regex):
        import re
        match = re.match(regex, self.text[self.pos:])
        if not match:
            return None
        found = match.group(0)
        self.pos += len(found)
        return found

    def tokens(self):
        """Returns a generator which will produce a stream of (token identifier, token value) pairs."""

        while self.pos < len(self.text):
            self.skip_whitespace()
            t, s = self.check_symbol()
            if s:
                yield t, s
                continue
            t = self.check_regex(r'[0-9]+')
            if t:
                yield 'number', int(t)
                continue
            t = self.check_regex(r'\w+')
            if t:
                yield 'ident', t
                continue
            try:
                t = self.text[self.pos]
            except Exception:
                t = 'end of file'  # at end of file this will fail because self.pos >= len(self.text)
                yield 'illegal', t
                break

    def __iter__(self) -> 'LexerIter':
        return LexerIter(self)


class LexerIter():
    def __init__(self, lexer):
        self.lxr = lexer.tokens()

        # Current symbol/value, updated on succesful accept
        self.sym = None
        self.val = None

        # Buffer values for rollback
        self.prev_val = None  # Updated on every non rollback next
        self.prev_sym = None  # See prev_val
        self.has_prev = False  # Becomes true after a non rollback next,
        # is false after a rollback
        self.rollback = False

    def roll_back(self):
        if not self.has_prev:
            raise LexerException("Can't rollback more")
        self.rollback = True
        self.has_prev = False

    def preview(self, sym, *alts) -> bool:
        r = self.accept(sym, *alts)
        if r is None:
            return False
        else:
            self.roll_back()
            return True

    def accept(self, sym, *alts) -> Optional[tuple]:
        """If the first item is the expected symbol return the symbol/value,
        otherwise rollback and return false"""
        s, v = next(self)
        if (s == sym) or (s in alts):
            self.sym = s
            self.val = v
            return s, v
        else:
            self.roll_back()
            return None

    def expect(self, sym, *alts) -> tuple:
        """
        Call accept and Error on False
        """
        r = self.accept(sym, *alts)
        if r is None:
            raise LexerException("Expecting ", sym, " failed")
        return r

    def __next__(self):
        if self.rollback:
            v = self.prev_val
            s = self.prev_sym
            self.rollback = False
            self.has_prev = True
            return s, v

        s, v = next(self.lxr)
        self.prev_val = v
        self.prev_sym = s
        self.has_prev = True
        return s, v


# Test support
__test_program = '''VAR x, y, squ;
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

if __name__ == '__main__':
    for t, w in Lexer(__test_program).tokens():
        print(t, w)
