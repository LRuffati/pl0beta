class Code:
    def __init__(self):
        self.lines = []
        self.ident = 0

    def comment(self, comment: str):
        self.lines.append('@' + '\t'*self.ident + comment)

    def label(self, label: str):
        self.new_line()
        self.lines.append(label + ':')

    def instruction(self, instr: str):
        self.lines.append('\t' * self.ident + instr)

    def multi_instr(self, *instr: tuple[str]):
        for i in instr:
            self.instruction(i)

    def increase_ident(self):
        self.ident += 1

    def decrease_ident(self):
        self.ident = max(self.ident-1, 0)

    def set_ident(self, level: int):
        self.ident = max(level, 0)

    def get_ident(self) -> int:
        return self.ident

    def global_var(self, name, bsize: int):
        """

        :param name:
        :param bsize: Size in bytes
        :return:
        """
        t = f".comm {name}, {bsize}"
        self.instruction(t)

    def new_line(self):
        self.lines.append('')