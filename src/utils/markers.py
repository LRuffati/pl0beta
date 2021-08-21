import abc


class Codegen(abc.ABC):

    #TODO: @abc.abstractmethod
    def emit_code(self):
        pass


class DataLayout(abc.ABC):
    @abc.abstractmethod
    def perform_data_layout(self):
        pass


