# Used when no version is defined by the SerializedFile or its BundleFile
FALLBACK_UNITY_VERSION = "2022.1.3f1"

DEBUG = True # Toggles debugging branches

# Determines if the TypeTrees for the Object types will be parsed.
#  Disabling this will reduce the load time by a lot (half of the time is spend
#  on parsing the typetrees) but it will also prevent saving some edited files,
#  unless we provide the TypeTrees by ourselves.
SERIALIZED_FILE_PARSE_TYPETREE = True

BIG_OBJECT_GUARD = 0 #int(2e9) # 0 or don't try to unpack bigger objects (bytes)

ENABLE_TYPETREEHELPER_FALLBACK = True # Fallback to TypeTreeHelper parsing in asset bundles

EXTENDED_SEARCH = False # Search all cwd subdirectories for resources

DEBUG_TYPETREES = False # Toggles TypeTree debugging in ObjectReader and TypeTreeHelper

ENABLE_BINARY_BLOBS = False # Enables custom UnityPyBinaryBlob type in TypeTrees

ENABLE_LOGGING_MODULE = 0 # 0 = console print; 1 = console log; 2 = file log (default: .\unitypy_log.txt)

# INFO: internal
WARNED_NOTFOUND_ONCE = True

# GLOBAL WARNING SUPPRESSION
FALLBACK_VERSION_WARNED = False  # for FALLBACK_UNITY_VERSION

# GET FUNCTIONS
def get_fallback_version():
    global FALLBACK_VERSION_WARNED
    if not FALLBACK_VERSION_WARNED:
        print(
            f"Warning: 0.0.0 version found, defaulting to UnityPy.config.FALLBACK_UNITY_VERSION ({FALLBACK_UNITY_VERSION})"  # noqa: E501
        )
        FALLBACK_VERSION_WARNED = True
    return FALLBACK_UNITY_VERSION
