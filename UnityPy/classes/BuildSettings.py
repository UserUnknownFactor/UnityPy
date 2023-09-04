from .Object import Object
from ..streams import EndianBinaryWriter
from .PPtr import PPtr, save_ptr


class BuildSettings(Object):
    def __init__(self, reader):
        super().__init__(reader=reader)
        self.scenes = reader.read_string_array()
        self.m_preloadedPlugins = reader.read_string_array()
        self.m_enabledVRDevices = reader.read_string_array()
        self.m_buildTags = reader.read_string_array()
        self.buildGUID = reader.read_bytes(16)
        self.hasPROVersion = reader.read_boolean()
        self.isNoWatermarkBuild = reader.read_boolean()
        """
        self.isPrototypingBuild = reader.read_boolean()
        self.isEducationalBuild = reader.read_boolean()
        self.isEmbedded = reader.read_boolean()
        self.isTrial = reader.read_boolean()
        self.hasPublishingRights = reader.read_boolean()
        self.hasShadows = reader.read_boolean()
        self.hasSoftShadows = reader.read_boolean()
        self.hasLocalLightShadows = reader.read_boolean()
        self.hasAdvancedVersion = reader.read_boolean()
        self.enableDynamicBatching = reader.read_boolean()
        self.isDebugBuild = reader.read_boolean()
        self.usesOnMouseEvents = reader.read_boolean()
        self.hasClusterRendering = reader.read_boolean()

        self.m_Version = reader.read_aligned_string()
        self.m_AuthToken = reader.read_aligned_string()
        self.m_GraphicsAPIs = reader.read_int_array()
        """
        self.the_rest = reader.read_the_rest(reader)

    def save(self, writer: EndianBinaryWriter = None):
        if writer is None:
            writer = EndianBinaryWriter(endian=self.reader.endian)
        super().save(writer)
        writer.write_string_array(self.scenes)
        writer.write_string_array(self.m_preloadedPlugins)
        writer.write_string_array(self.m_enabledVRDevices)
        writer.write_string_array(self.m_buildTags)
        writer.write_bytes(self.buildGUID)
        writer.write_boolean(self.hasPROVersion)
        writer.write_boolean(self.isNoWatermarkBuild)
        """
        writer.write_boolean(self.isPrototypingBuild)
        writer.write_boolean(self.isEducationalBuild)
        writer.write_boolean(self.isEmbedded)
        writer.write_boolean(self.isTrial)
        writer.write_boolean(self.hasPublishingRights)
        writer.write_boolean(self.hasShadows)
        writer.write_boolean(self.hasSoftShadows)
        writer.write_boolean(self.hasLocalLightShadows)
        writer.write_boolean(self.hasAdvancedVersion)
        writer.write_boolean(self.enableDynamicBatching)
        writer.write_boolean(self.isDebugBuild)
        writer.write_boolean(self.usesOnMouseEvents)
        writer.write_boolean(self.hasClusterRendering)

        writer.write_aligned_string(self.m_Version)
        writer.write_aligned_string(self.m_AuthToken)
        writer.write_int_array(self.m_GraphicsAPIs)
        """

        writer.write_bytes(self.the_rest)
        self.set_raw_data(writer.bytes)