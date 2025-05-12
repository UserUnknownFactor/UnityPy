from .Behaviour import Behaviour
from .PPtr import PPtr
from ..streams import EndianBinaryReader, EndianBinaryWriter
from ..exceptions import TypeTreeError as TypeTreeError

class MonoBehaviour(Behaviour):
    def __init__(self, reader: EndianBinaryReader):
        super().__init__(reader=reader)
        self.m_Script = PPtr(reader)
        self.m_Name = reader.read_aligned_string()

        self._raw_offset = reader.Position
        if self.assets_file.type_trees_saved and self.assets_file._use_type_trees:
            try:
                self.read_typetree(all_trees=self.assets_file.get_all_typetrees())
            except TypeTreeError as e:
                print_info(f"failed to read TypeTree for {self.m_Name} [path_id={self.m_PathID}]: {e}")
                self.assets_file._use_type_trees = False
                self.raw_monobehaviour = self.reader.read_the_rest()
        else:
            self.raw_monobehaviour = self.reader.read_the_rest()

    def __getitem__(self, item):
        return getattr(self, item)

    def save(self, writer: EndianBinaryWriter = None, raw_data: bytes = None):
        if raw_data is None:
            if not self.raw_monobehaviour:
                ValueError("No raw MonoBehaviour data provided")
            else:
                raw_data = self.raw_monobehaviour

        if writer is None:
            writer = EndianBinaryWriter(endian=self.reader.endian)

        super().save(writer)
        self.m_Script.save(writer)
        writer.write_aligned_string(self.m_Name)
        writer.write(raw_data)

        self.set_raw_data(writer)

    def get_raw_monobehaviour(self) -> bytes:
        """
        Reads the undocumentated data following the default init.
        This is usefull for classes that are stored via MonoBehaviours.
        """
        reader = self.reader
        reader.Position = self._raw_offset
        return reader.read_bytes(reader.byte_size - (self._raw_offset - reader.byte_start))

