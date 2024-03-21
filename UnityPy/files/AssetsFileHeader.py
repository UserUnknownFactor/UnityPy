class AssetsFileHeader:
    def __init__(self, reader):
        self.metadataSize = 0
        self.fileSize = 0
        self.version = 0
        self.dataOffset = 0
        self.endian = False
        if reader:
            self.read(reader)

    def read(self, reader):
        reader.endian = "<"
        self.metadataSize = reader.read_uint()
        self.fileSize = reader.read_uint()
        self.version = reader.read_uint()
        self.dataOffset = reader.read_uint()
        self.endian = reader.ReadBoolean()
        reader.Position += 3  # unused bytes

        if self.Version >= 0x16:
            self.metadataSize = reader.read_uint()
            self.fileSize = reader.read_long()
            self.dataOffset = reader.read_long()
            reader.Position += 8  # unused bytes

    def save(self, writer):
        if self.version >= 0x16:
            writer.write(b"\0\0")
            writer.write_uint(self.version)
            writer.write(b'\0')
        else:
            writer.write_uint(self.metadataSize)
            writer.write_uint(self.fileSize)
            writer.write_uint(self.Version)
            writer.write_uint(self.dataOffset)

        writer.write_uint(self.endian)
        writer.write(b'\0' * 3)

        if self.Version >= 0x16:
            writer.write_long(self.metadataSize)
            writer.write_long(self.fileSize)
            writer.write_long(self.dataOffset)
            writer.write(b'\0' * 8)