Stages:
1. Lexer
2. Parser
3. Lowering
4. Data layout
5. CFG
    1. Liveness
6. Register allocation
7. Code generation

# Lexer
Linear iterator over the text source code which tokenizes the elements of the 
stream, strips the whitespaces

Returns a single object which is passed around within the parser

# Parser
An LL(1) parser, can:
+ `accept`, accepts an identifier, fallible, returns a status code
+ `expect`, accepts an identifier but errors if it doesn't get it
+ `getsym`, internal, updates the current symbol and the current value,
fails if there's no next symbol

At the end of the parsing pass I have to have a tree of IRNodes

## getsym & co
I have:
+ sym, only changed by getsym
+ value, 
+ new_sym
+ new_value

### value
Obtained from the lexer, updated in getsym, read at various places

### new_sym
Updated only in getsym

Checked in term, expression and condition

### new_value
Only errors

### Conclusions
These behave as a lookahead

The code would check if 

























