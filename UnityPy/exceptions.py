class TypeTreeError(Exception):
    def __init__(self, message, nodes):
        super().__init__(message)
        self.nodes = nodes

