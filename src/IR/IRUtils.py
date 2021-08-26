from src.Symbols.Symbols import Symbol, RegisterSymb

tempcount = 0


def new_temporary(symtab, typ) -> RegisterSymb:
    global tempcount
    temp = RegisterSymb(name=f't{tempcount}', stype=typ, alloct='reg')
    tempcount += 1
    return temp
