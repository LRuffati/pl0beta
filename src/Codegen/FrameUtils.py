from typing import Optional as Opt

import src
from src.utils.Exceptions import CodegenException


class StackLayout:
    """
    This class represents the stack layout of the program
    It will contain all the info necessary for code generation

    At the global level it'll just contain the space needed for spill
    variables and for the register saving
    """

    def __init__(self, older: Opt['FrozenLayout'] = None):
        if older:
            self.level = older.level + 1
        else:
            self.level = 0
        self.parent = older

        self.before_fp: list[str] = []
        self.after_fp: list[str] = []  # these lists grow away from the frame pointer
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
            off += sect.max_size
        if before:
            off = (off + section.max_size) * (-1)
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

    def get_level(self, lvl: Opt[int]) -> 'StackLayout':
        if self.level < lvl:
            raise CodegenException("Trying to get a lever higher than self")
        if self.level == lvl:
            return self
        else:
            return self.parent.get_level(lvl)

    def frame_size(self):
        """
        :return: The size of the frame in register equivalent words after
        the frame pointer
        """
        last_sect = self.after_fp[-1]
        sec = self.get_section(last_sect)
        off = self.offset(last_sect)
        return off + sec.max_size


class FrozenLayout(StackLayout):
    def __init__(self, layout: StackLayout, sections: list[str]):
        """
        Create a frozen layout from the given one by selecting only the given sections
        :param layout:
        :param sections:
        """
        self.level = layout.level
        self.parent = layout.parent
        self.before_fp: list[(str, int)] = [(i, layout.offset(i)) for i in layout.before_fp if i in sections]
        self.after_fp: list[(str, int)] = [(i, layout.offset(i)) for i in layout.after_fp if i in sections]
        self.sections: dict[str, tuple['FrozenSection', bool]] = \
            {k: (FrozenSection(v[0]), v[1]) for k, v in layout.sections.items()
             if k in sections}
        self._frame_s = layout.frame_size()

    def add_section(self, section: 'StackSection', before=False):
        raise CodegenException("Trying to edit a frozen layout")

    def offset(self, name: str) -> int:
        sec, bef = self.sections[name]
        if bef:
            lst = self.before_fp
        else:
            lst = self.after_fp
        for nam, off in lst:
            if nam == name:
                return off

    def frame_size(self):
        return self._frame_s


class StackSection:
    """
    A contiguous section of the stack in a frame
    """

    def __init__(self, name, size=0, visibility=False):
        self.name = name
        self._size = size
        self.vis = visibility
        self.max_size = 0
        self.symbols: dict['Symbol', int] = {}

    def grow(self, *, words: int = None, symb: 'Symbol' = None) -> bool:
        """
        Grow the size by the given number of words (1 word = space for 1 register)
        or by adding the given Symbol
        :param words:
        :param symb:
        :return: If the section was grown
        """
        size = 0
        if symb is not None:
            size = (symb.stype.size // 32)  # 1 register = 32 bits
            if symb.stype.size % 32:
                size += 1

            if symb in self.symbols:
                return False
            self.symbols[symb] = self._size
        elif words is None:
            raise CodegenException("Need either a symbol or size to add to stack section")
        else:
            size = words
        self._size += size
        self.max_size = max(self._size, self.max_size)
        return True

    def shrink(self, *, words: int = None, symb: 'Symbol' = None):
        """
        Decrease the size
        :param words:
        :param symb:
        :return:
        """
        if symb in self.symbols:
            self._size -= symb.stype.size // 32
        elif symb is not None:
            raise CodegenException("Trying to remove from section a symbol that was never added")
        elif words is None:
            raise CodegenException("Need either a symbol or a size to shrink a stack section")
        else:
            self._size -= words

    def set_size(self, size=0):
        """
        Sets a size and the maximum. The size of the section will be the maximum of the previous
        size and the size provided
        :param size: the number of register-equivalent words
        :return:
        """
        self.max_size = max(size, self.max_size)
        self._size = max(size, self._size)

    def get_offset(self, symb: 'Symbol'):
        if symb not in self.symbols:
            raise CodegenException("Symbol not in section")
        return self.symbols[symb]


class FrozenSection(StackSection):
    def __init__(self, section: StackSection):
        self.name = section.name
        self.max_size = section.max_size
        self.symbols: dict['Symbol', int] = section.symbols.copy()

    def grow(self, *, words: int = None, symb: 'Symbol' = None) -> bool:
        raise CodegenException("Can't grow frozen section")

    def shrink(self, *, words: int = None, symb: 'Symbol' = None):
        raise CodegenException("Can't shrink frozen section")

    def set_size(self, size=0):
        raise CodegenException("Can't set size of frozen section")


if __name__ == '__main__':
    Symbol = src.Symbols.Symbols.Symbol
