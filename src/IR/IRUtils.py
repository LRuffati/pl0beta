tempcount = 0


def new_temporary(symtab, typ):
    global tempcount
    temp = Symbol(name=f't{tempcount}', stype=typ, alloct='reg')
    tempcount += 1
    return temp
