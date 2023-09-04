from .Object import Object
from ..streams import EndianBinaryWriter

class UVs:
    def __init__(self, reader):
        #self.serializedVersion = reader.read_int()
        self.x = reader.read_float()
        self.y = reader.read_float()
        self.width = reader.read_float()
        self.height = reader.read_float()

    def save(self, writer):
        #self.serializedVersion = reader.read_int()
        writer.write_float(self.x)
        writer.write_float(self.y)
        writer.write_float(self.width)
        writer.write_float(self.height)

class SplashScreenLogo:
    def __init__(self, reader):
        self.PPtr = reader.read_bytes(16)
        self.duration = reader.read_float()

    def save(self, writer):
        writer.write_bytes(self.PPtr)
        writer.write_float(self.duration)

class AspectRatio:
    def __init__(self, reader):
        self.PPtr = reader.read_bytes(16)
        self.duration = reader.read_float()

    def save(self, writer):
        writer.write_bytes(self.PPtr)
        writer.write_float(self.duration)

class PlayerSettings(Object):
    def __init__(self, reader):
        super().__init__(reader=reader)
        version = self.version
        if version >= (5, 4):  # 5.4.0 nad up
            self.productGUID = reader.read_bytes(16)

        self.AndroidProfiler = reader.read_boolean()
        # bool AndroidFilterTouchesWhenObscured 2017.2 and up
        # bool AndroidEnableSustainedPerformanceMode 2018 and up
        reader.align_stream()
        self.defaultScreenOrientation = reader.read_int()
        self.targetDevice = reader.read_int()
        if version < (5, 3):  # 5.3 down
            if version < (5,):  # 5.0 down
                self.targetPlatform = reader.read_int()  # 4.0 and up targetGlesGraphics
                if version >= (4, 6):  # 4.6 and up
                    self.targetIOSGraphics = reader.read_int()
            self.targetResolution = reader.read_int()
        else:
            self.useOnDemandResources = reader.read_boolean()
            reader.align_stream()
        if version >= (3, 5):  # 3.5 and up
            self.accelerometerFrequency = reader.read_int()
        self.companyName = reader.read_aligned_string()
        self.productName = reader.read_aligned_string()

        self.defaultCursor = reader.read_bytes(16)
        self.cursorHotspot = reader.read_int()
        self.m_SplashScreenBackgroundColor = reader.read_vector4()

        self.m_ShowUnitySplashScreen = reader.read_boolean()
        self.m_ShowUnitySplashLogo = reader.read_boolean()
        reader.align_stream()
        """
        self.m_SplashScreenOverlayOpacity = reader.read_float()
        self.m_SplashScreenAnimation = reader.read_int()
        self.m_SplashScreenLogoStyle = reader.read_int()
        self.m_SplashScreenDrawMode = reader.read_int()
        self.m_SplashScreenBackgroundAnimationZoom = reader.read_float()
        self.m_SplashScreenLogoAnimationZoom = reader.read_float()
        self.m_SplashScreenBackgroundLandscapeAspect = reader.read_float()
        self.m_SplashScreenBackgroundPortraitAspect = reader.read_float()
        self.m_SplashScreenBackgroundLandscapeUvs = UVs(reader)
        self.m_SplashScreenBackgroundPortraitUvs = UVs(reader)
        self.m_SplashScreenLogos = reader.read_array(lambda: SplashScreenLogo(), reader.read_int())
        self.m_SplashScreenBackgroundLandscape = reader.read_bytes(16)
        self.m_SplashScreenBackgroundPortrait = reader.read_bytes(16)
        self.m_VirtualRealitySplashScreen = reader.read_bytes(16)
        reader.align_stream()
        #self.m_HolographicTrackingLossScreen = reader.read_bytes(16)

        self.defaultScreenWidth = reader.read_int()
        self.defaultScreenHeight = reader.read_int()
        self.defaultScreenWidthWeb = reader.read_int()
        self.defaultScreenHeightWeb = reader.read_int()
        self.m_StereoRenderingPath = reader.read_int()
        self.m_ActiveColorSpace = reader.read_int()

        self.m_MTRendering = reader.read_boolean()

        #self.mobileMTRenderingBaked = reader.read_boolean()
        #self.playerMinOpenGLESVersion = reader.read_int()

        self.mipStripping = reader.read_boolean()
        reader.align_stream()
        self.numberOfMipsStripped = reader.read_int()
        self.m_StackTraceTypes = reader.read_array(lambda: reader.read_int(), reader.read_int()) #reader.read_bytes(16)

        self.iosShowActivityIndicatorOnLoading = reader.read_int()
        self.androidShowActivityIndicatorOnLoading = reader.read_int()
        self.iosUseCustomAppBackgroundBehavior = reader.read_boolean()
        self.iosAllowHTTPDownload = reader.read_boolean()

        self.allowedAutorotateToPortrait = reader.read_boolean()
        self.allowedAutorotateToPortraitUpsideDown = reader.read_boolean()
        self.allowedAutorotateToLandscapeRight = reader.read_boolean()
        self.allowedAutorotateToLandscapeLeft = reader.read_boolean()
        self.useOSAutorotation = reader.read_boolean()
        self.use32BitDisplayBuffer = reader.read_boolean()
        self.preserveFramebufferAlpha = reader.read_boolean()
        self.disableDepthAndStencilBuffers = reader.read_boolean()

        self.androidStartInFullscreen = reader.read_boolean()
        self.androidRenderOutsideSafeArea = reader.read_boolean()
        self.androidUseSwappy = reader.read_boolean()
        self.androidBlitType = reader.read_int()
        self.androidResizableWindow = reader.read_boolean()
        self.androidDefaultWindowWidth = reader.read_int()
        self.androidDefaultWindowHeight = reader.read_int()
        self.androidMinimumWindowWidth = reader.read_int()
        self.androidMinimumWindowHeight = reader.read_int()
        self.androidFullscreenMode = reader.read_boolean()
        self.defaultIsNativeResolution = reader.read_boolean()
        self.macRetinaSupport = reader.read_boolean()

        self.runInBackground = reader.read_boolean()
        self.captureSingleScreen = reader.read_boolean()
        self.muteOtherAudioSources = reader.read_boolean()
        self.PrepareIOSForRecording = reader.read_boolean()
        self.ForceIOSSpeakersWhenRecording = reader.read_boolean()
        reader.align_stream()
        self.deferSystemGesturesMode = reader.read_boolean()
        self.hideHomeButton = reader.read_boolean()

        self.submitAnalytics = reader.read_boolean()
        self.usePlayerLog = reader.read_boolean()

        self.bakeCollisionMeshes = reader.read_boolean()
        self.forceSingleInstance = reader.read_boolean()
        self.useFlipModelSwapchain = reader.read_boolean()
        self.resizableWindow = reader.read_boolean()

        self.useMacAppStoreValidation = reader.read_boolean()
        reader.align_stream()
        self.macAppStoreCategory = reader.read_aligned_string()
        self.gpuSkinning = reader.read_boolean()

        self.xboxPIXTextureCapture = reader.read_boolean()
        self.xboxEnableAvatar = reader.read_boolean()
        self.xboxEnableKinect = reader.read_boolean()
        self.xboxEnableKinectAutoTracking = reader.read_boolean()
        self.xboxEnableFitness = reader.read_boolean()

        self.visibleInBackground = reader.read_boolean()
        self.allowFullscreenSwitch = reader.read_boolean()
        reader.align_stream()
        self.fullscreenMode = reader.read_byte()
        reader.align_stream()

        """"""
        self.xboxSpeechDB = reader.read_int()
        self.xboxEnableHeadOrientation = reader.read_boolean()
        reader.align_stream()
        self.xboxEnableGuest = reader.read_boolean()
        reader.align_stream()
        self.xboxEnablePIXSampling = reader.read_boolean()
        reader.align_stream()
        self.metalFramebufferOnly = reader.read_boolean()
        reader.align_stream()

        self.xboxOneResolution = reader.read_int()
        self.xboxOneSResolution = reader.read_int()
        self.xboxOneXResolution = reader.read_int()
        self.xboxOneMonoLoggingLevel = reader.read_int()
        self.xboxOneLoggingLevel = reader.read_int()
        self.xboxOneDisableEsram = reader.read_boolean()
        reader.align_stream()
        self.xboxOneEnableTypeOptimization = reader.read_boolean()
        reader.align_stream()
        self.xboxOnePresentImmediateThreshold = reader.read_u_int()

        self.switchQueueCommandMemory = reader.read_int()
        self.switchQueueControlMemory = reader.read_int()
        self.switchQueueComputeMemory = reader.read_int()
        self.switchNVNShaderPoolsGranularity = reader.read_int()
        self.switchNVNDefaultPoolsGranularity = reader.read_int()
        self.switchNVNOtherPoolsGranularity = reader.read_int()
        self.switchNVNMaxPublicTextureIDCount = reader.read_int()
        self.switchNVNMaxPublicSamplerIDCount = reader.read_int()
        self.stadiaPresentMode = reader.read_int()
        self.stadiaTargetFramerate = reader.read_int()
        reader.align_stream()

        self.vulkanNumSwapchainBuffers = reader.read_u_int()
        self.vulkanEnableSetSRGBWrite = reader.read_boolean()
        self.vulkanEnablePreTransform = reader.read_boolean()
        self.vulkanEnableLateAcquireNextImage = reader.read_boolean()
        self.vulkanEnableCommandBufferRecycling = reader.read_boolean()
        reader.align_stream()

        self.m_SupportedAspectRatios = reader.read_bytes(5)
        self.bundleVersion =  reader.read_aligned_string()
        self.preloadedAssets = reader.read_array(lambda: reader.read_bytes(16), reader.read_int())
        reader.align_stream()
        
        self.metroInputSource = reader.read_bytes(16) #reader.read_boolean()
        self.wsaTransparentSwapchain = reader.read_boolean() #reader.read_boolean()
        reader.align_stream()
        self.m_HolographicPauseOnTrackingLoss = reader.read_boolean()
        self.xboxOneDisableKinectGpuReservation = reader.read_boolean()
        self.xboxOneEnable7thCore = reader.read_boolean()
        reader.align_stream()
        #self.vrSettings
        self.enable360StereoCapture = reader.read_boolean()
        reader.align_stream()
        self.isWsaHolographicRemotingEnabled = reader.read_boolean()
        reader.align_stream()
        self.enableFrameTimingStats = reader.read_boolean()
        reader.align_stream()
        self.useHDRDisplay = reader.read_boolean()
        reader.align_stream()
        self.D3DHDRBitDepth = reader.read_int()
        self.m_ColorGamuts = reader.read_array(reader.read_int, reader.read_int())
        self.targetPixelDensity = reader.read_int()
        self.resolutionScalingMode = reader.read_int()
        self.androidSupportedAspectRatio = reader.read_int()
        self.androidMaxAspectRatio = reader.read_float()
        reader.align_stream()
        
        self.activeInputHandler = reader.read_int()
        self.cloudProjectId = reader.read_aligned_string()
        self.framebufferDepthMemorylessMode = reader.read_int()
        self.qualitySettingsNames = reader.read_array(lambda: reader.read_bytes(16), reader.read_int())
        reader.align_stream()
        
        self.projectName = reader.read_aligned_string()
        self.organizationId = reader.read_boolean()
        self.cloudEnabled = reader.read_boolean()
        self.legacyClampBlendShapeWeights = reader.read_int()
        reader.align_stream()
        self.playerDataPath = reader.read_aligned_string()
        self.forceSRGBBlit = reader.read_boolean()
        self.virtualTexturingSupportEnabled = reader.read_boolean()
        self.uploadClearedTextureDataAfterCreationFromScript = reader.read_boolean()
        """
        self.the_rest = reader.read_the_rest(reader)

    def save(self, writer: EndianBinaryWriter = None):
        if writer is None:
            writer = EndianBinaryWriter(endian=self.reader.endian)
        super().save(writer, intern_call=True)
        version = self.version
        if version >= (5, 4):  # 5.4.0 nad up
            writer.write_bytes(self.productGUID)

        writer.write_boolean(self.AndroidProfiler)
        # bool AndroidFilterTouchesWhenObscured 2017.2 and up
        # bool AndroidEnableSustainedPerformanceMode 2018 and up
        writer.align_stream()
        writer.write_int(self.defaultScreenOrientation)
        writer.write_int(self.targetDevice)
        if version < (5, 3):  # 5.3 down
            if version < (5,):  # 5.0 down
                writer.write_int(self.targetPlatform)  # 4.0 and up targetGlesGraphics
                if version >= (4, 6):  # 4.6 and up
                    writer.write_int(self.targetIOSGraphics)
            writer.write_int(self.targetResolution)
        else:
            writer.write_boolean(self.useOnDemandResources)
            writer.align_stream()
        if version >= (3, 5):  # 3.5 and up
            writer.write_int(self.accelerometerFrequency)
        writer.write_aligned_string(self.companyName)
        writer.write_aligned_string(self.productName)

        writer.write_bytes(self.defaultCursor)
        writer.write_int(self.cursorHotspot)
        writer.write_vector4(self.m_SplashScreenBackgroundColor)

        writer.write_boolean(self.m_ShowUnitySplashScreen)
        writer.write_boolean(self.m_ShowUnitySplashLogo)
        writer.align_stream()

        writer.write_bytes(self.the_rest)
        self.set_raw_data(writer.bytes)

