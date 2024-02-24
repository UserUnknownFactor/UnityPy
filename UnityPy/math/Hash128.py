class Hash128:
    def __init__(self, data=b''):
        if isinstance(data, Hash128):
            self.data = data.data
        else:
            self.data = bytes(data)

    def read(self, reader):
        self.data = reader.read(16)

    def write(self, writer):
        writer.write(self.data)

    @property
    def is_zero(self):
        return self.data is None or all([a == 0 for a in self.data])

    def __str__(self):
        return ''.join(f"{hb:02X}" for hb in self.data)

    def __bytes__(self):
        return self.data

    @classmethod
    def blank_hash(cls):
        return cls(b'\0' * 16)