import abc


class Codegen(abc.ABC):

    #TODO: @abc.abstractmethod
    def emit_code(self):
        pass


class Lowered(Codegen):
    def set_label(self, label):
        raise NotImplementedError()

    def destination(self):
        raise NotImplementedError()

