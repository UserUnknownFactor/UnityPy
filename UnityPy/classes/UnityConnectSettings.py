from .Object import Object
from ..streams import EndianBinaryWriter
from ..files import ObjectReader

class CrashReportingSettings():
    def __init__(self, reader: ObjectReader):
        self.m_EventUrl = reader.read_aligned_string() 
        self.m_Enabled = reader.read_bool() 
        reader.align_stream()
        self.m_LogBufferSize = reader.read_u_int() 
        reader.align_stream()
        
    def save(self, writer: EndianBinaryWriter):
        writer.write_aligned_string(self.m_EventUrl) 
        writer.write_bool(self.m_Enabled) 
        writer.align_stream()
        writer.write_u_int(self.m_LogBufferSize) 
        writer.align_stream()

class UnityPurchasingSettings():
    def __init__(self, reader: ObjectReader):
        self.m_Enabled = reader.read_bool() 
        self.m_TestMode = reader.read_bool() 
        reader.align_stream()
        
    def save(self, writer: EndianBinaryWriter):
        writer.write_bool(self.m_Enabled) 
        writer.write_bool(self.m_TestMode) 
        writer.align_stream()
        
class UnityAnalyticsSettings():
    def __init__(self, reader: ObjectReader):
        self.m_Enabled = reader.read_bool() 
        self.m_TestMode = reader.read_bool() 
        self.m_InitializeOnStartup = reader.read_bool() 
        self.m_PackageRequiringCoreStatsPresent = reader.read_bool() 
        reader.align_stream()

    def save(self, writer: EndianBinaryWriter):
        writer.write_bool(self.m_Enabled) 
        writer.write_bool(self.m_TestMode) 
        writer.write_bool(self.m_InitializeOnStartup) 
        writer.write_bool(self.m_PackageRequiringCoreStatsPresent) 
        writer.align_stream()

class UnityAdsSettings():
    def __init__(self, reader: ObjectReader):
        self.m_Enabled = reader.read_bool() 
        self.m_InitializeOnStartup = reader.read_bool() 
        self.m_TestMode = reader.read_bool() 
        reader.align_stream()
        self.m_GameId = reader.read_aligned_string()
        
    def save(self, writer: EndianBinaryWriter):
        writer.write_bool(self.m_Enabled) 
        writer.write_bool(self.m_InitializeOnStartup) 
        writer.write_bool(self.m_TestMode) 
        writer.align_stream()
        writer.write_aligned_string(self.m_GameId)

class PerformanceReportingSettings():
    def __init__(self, reader: ObjectReader):
        self.m_Enabled = reader.read_bool() 
        reader.align_stream()
        
    def save(self, writer: EndianBinaryWriter):
        writer.write_bool(self.m_Enabled) 
        writer.align_stream()
        
class UnityConnectSettings(Object):
    def __init__(self, reader: ObjectReader):
        super().__init__(reader=reader)
        version = self.version
        self.m_Enabled = reader.read_bool() 
        self.m_TestMode = reader.read_bool() 
        reader.align_stream()
        self.m_EventOldUrl = reader.read_aligned_string() 
        self.m_EventUrl = reader.read_aligned_string() 
        self.m_ConfigUrl = reader.read_aligned_string() 
        self.m_DashboardUrl = reader.read_aligned_string() 
        self.m_TestInitMode = reader.read_int() 
        reader.align_stream()
        self.m_CrashReportingSettings = CrashReportingSettings(reader)
        self.m_UnityPurchasingSettings = UnityPurchasingSettings(reader)
        self.m_UnityAnalyticsSettings = UnityAnalyticsSettings(reader)
        self.m_UnityAdsSettings = UnityAdsSettings(reader)
        self.m_PerformanceReportingSettings = PerformanceReportingSettings(reader)

    def save(self, writer: EndianBinaryWriter = None):
        if writer is None:
            writer = EndianBinaryWriter(endian=self.reader.endian)
        super().save(writer, intern_call=True)
        writer.write_bool(self.m_Enabled) 
        writer.write_bool(self.m_TestMode) 
        writer.align_stream()
        writer.write_aligned_string(self.m_EventOldUrl) 
        writer.write_aligned_string(self.m_EventUrl) 
        writer.write_aligned_string(self.m_ConfigUrl) 
        writer.write_aligned_string(self.m_DashboardUrl) 
        writer.write_int(self.m_TestInitMode) 
        writer.align_stream()
        self.m_CrashReportingSettings.save(writer)
        self.m_UnityPurchasingSettings.save(writer)
        self.m_UnityAnalyticsSettings.save(writer)
        self.m_UnityAdsSettings.save(writer)
        self.m_PerformanceReportingSettings.save(writer)
        
        self.set_raw_data(writer.bytes)
