"""
Register constants for codegen
"""

FP = 11
SCR = 12  # Scratch
SP = 13
LR = 14  # return address of a function
PC = 15

A1 = 0
A2 = 1
A3 = 2
A4 = 3

for i in range(16):
    exec(f'R{i} = {i}')