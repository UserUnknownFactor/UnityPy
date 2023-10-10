from . import config

class TypeTreeError(Exception):
    def __init__(self, message, nodes):
        super().__init__(message)
        self.nodes = nodes

def sanity_check(value_name: str, value: int, max_value: int=32767) -> None:
        if config.DEBUG and (value >= max_value):
            raise ValueIsTooBig(f"{value_name} length", value)

class ValueIsTooBig(Exception):
    def __init__(self, variable_name, value):
        sep_value =  f"{value:,}"#.replace(',', ' ')
        super().__init__(f"{variable_name} value = {sep_value} is unrealistically big")
        self.value = value

class ReadingPastObject(Exception):
    def __init__(self, obj):
        super().__init__(f"read data past {obj} length")
        self.value = value
