# used when no version is defined by the SerializedFile or its BundleFile
FALLBACK_UNITY_VERSION = "2022.1.3f1"

# determines if the TypeTrees for the Object types will be parsed
#  disabling this will reduce the load time by a lot
#  (half of the time is spend on parsing the typetrees)
#  but it will also prevent saving an edited file
SERIALIZED_FILE_PARSE_TYPETREE = False

BIG_OBJECT_GUARD = 2 * 1000 * 1000 * 1000 # Don't try to unpack bigger objects than this; 0 to disable

ENABLE_TYPETREEHELPER_FALLBACK = False # Enable TypeTreeHelper parsing in asset bundles

EXTENDED_SEARCH = False # Search all cwd subdirectories for resources

DEBUG = True # Toggles debugging branches

DEBUG_TYPETREES = False # Toggles debugging branches in ObjectReader and TypeTreeHelper

WARNED_NOTFOUND_ONCE = True

# INFO: internal
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
