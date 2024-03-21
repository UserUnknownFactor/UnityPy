class AssetTypeReference:
    def __init__(self, className="", nameSpace="", asmName=""):
        self.m_ClassName = className
        self.m_Namespace = nameSpace
        self.m_AsmName = asmName

    def ReadMetadata(self, reader):
        self.m_ClassName = reader.read_string_to_null()
        self.m_Namespace = reader.read_string_to_null()
        self.m_AsmName = reader.read_string_to_null()

    def ReadAsset(self, reader):
        self.m_ClassName = reader.read_aligned_string()
        self.m_Namespace = reader.read_aligned_string()
        self.m_AsmName = reader.read_aligned_string()

    def WriteMetadata(self, writer):
        writer.writer_string_to_null(self.m_ClassName)
        writer.writer_string_to_null(self.m_Namespace)
        writer.writer_string_to_null(self.m_AsmName)

    def WriteAsset(self, writer):
        writer.write_aligned_string(self.m_ClassName)
        writer.write_aligned_string(self.m_Namespace)
        writer.write_aligned_string(self.m_AsmName)

    def __eq__(self, other):
        if not isinstance(other, AssetTypeReference):
            return False
        return self.m_ClassName == other.ClassName and self.m_Namespace == other.Namespace and self.m_AsmName == other.AsmName

    def __hash__(self):
        return hash((self.m_ClassName, self.m_Namespace, self.m_AsmName))

TERMINUS = AssetTypeReference("Terminus", "UnityEngine.DMAT", "FAKE_ASM")