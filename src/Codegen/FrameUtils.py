from typing import Optional as Opt

from src.utils.Exceptions import CodegenException


class StackLayout:
    """
    This class represents the stack layout of the program
    It will contain all the info necessary for code generation

    At the global level it'll just contain the space needed for spill
    variables and for the register saving
    """
    def __init__(self, older: Opt['FrozenLayout'] = None):
        self.older = older
        self.before_fp: list[str] = []
        self.after_fp: list[str] = [] # these lists grow away from the frame pointer
        self.sections: dict[str, tuple['StackSection', bool]] = {}

    def offset(self, name: str) -> int:
        section, before = self.sections[name]
        lst = None
        if before:
            lst = self.before_fp
        else:
            lst = self.after_fp

        off = 0
        for n in lst:
            if n == name:
                break
            sect, _ = self.sections[n]
            off += sect.size
        if before:
            off = (off + section.size)*(-1)
        return off

    def get_section(self, name: str) -> 'StackSection':
        return self.sections[name][0]

    def add_section(self, section: 'StackSection', before=False):
        """
        Adds a new section to the layout
        :param section: The section to add
        :param before: If True add it before the frame pointer, meaning it ends up in the
        caller frame. If false add it after the frame pointer
        :return:
        """
        self.sections[section.name] = (section, before)
        if before:
            self.before_fp.append(section.name)
        else:
            self.after_fp.append(section.name)

    def has_section(self, name: str):
        return name in self.sections


class FrozenLayout:
    def __init__(self, layout: StackLayout, sections: list[str]):
        """
        Create a frozen layout from the given one by selecting only the given sections
        :param layout:
        :param sections:
        """


class StackSection:
    """
    A contiguous section of the stack in a frame
    """
    def __init__(self, name, size=0, visibility=False):
        self.name = name
        self.size = size
        self.vis = visibility
        self.max_size = 0
        self.symbols: dict['Symbol', int] = {}

    def grow(self, *, words: int = None, symb: 'Symbol' = None) -> bool:
        """
        Grow the size by the given number of words (1 word = 8 bytes)
        or by adding the given Symbol
        :param words:
        :param symb:
        :return: False if the section was grown, True otherwise
        """
        size = 0
        if symb is not None:
            size = symb.stype.size // 8
            if symb in self.symbols:
                return False
            self.symbols[symb] = self.max_size
        elif words is None:
            raise CodegenException("Need either a symbol or size to add to stack section")
        else:
            size = words
        self.size += size
        return True

    def shrink(self, *, words: int = None, symb: 'Symbol' = None):
        """
        Decrease the size
        :param words:
        :param symb:
        :return:
        """
        if symb in self.symbols:
            self.size -= symb.stype.size // 8
        elif symb is not None:
            raise CodegenException("Trying to remove from section a symbol that was never added")
        elif words is None:
            raise CodegenException("Need either a symbol or a size to shrink a stack section")
        else:
            self.size -= words

    def get_offset(self, symb: 'Symbol'):
        if symb not in self.symbols:
            raise CodegenException("Symbol not in section")
        return self.symbols[symb]