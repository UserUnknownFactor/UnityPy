class GUID128:
    HexToLiteral = "0123456789abcdef"
    __slots__ = {"data0", "data1", "data2", "data3"}

    def __init__(self, reader=None):
        if reader is not None:
            self.read(reader)

    @property
    def is_empty(self):
        return self.data0 == 0 and self.data1 == 0 and self.data2 == 0 and self.data3 == 0

    def read(self, reader):
        self.data0 = reader.read_uint()
        self.data1 = reader.read_uint()
        self.data2 = reader.read_uint()
        self.data3 = reader.read_uint()

    def write(self, writer):
        writer.write_uint(self.data0)
        writer.write_uint(self.data1)
        writer.write_uint(self.data2)
        writer.write_uint(self.data3)

    def __getitem__(self, i):
        if i == 0:
            return self.data0
        elif i == 1:
            return self.data1
        elif i == 2:
            return self.data2
        elif i == 3:
            return self.data3
        else:
            raise IndexError()

    def __setitem__(self, i, value):
        if i == 0:
            self.data0 = value
        elif i == 1:
            self.data1 = value
        elif i == 2:
            self.data2 = value
        elif i == 3:
            self.data3 = value
        else:
            raise IndexError()

    def __str__(self):
        string_builder = []
        for i in range(3, -1, -1):
            for j in range(7, -1, -1):
                cur = self[i]
                cur >>= (j * 4)
                cur &= 0xF
                string_builder.insert(0, self.HexToLiteral[cur])
        return ''.join(string_builder)

    @classmethod
    def from_bytes(guid, data):
        if len(data) != 32:
            return None

        guid = new guid()
        for i in range(4):
            cur = 0
            for j in range(7, -1, -1):
                cur_hex = GUID128.literal_to_hex(str[i * 8 + j])
                if cur_hex == uint.MaxValue:
                    return None
                cur |= (cur_hex << (j * 4))
            guid[i] = cur

        return guid

    @staticmethod
    def literal_to_hex(c):
        return int(c)