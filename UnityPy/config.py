# Used when no version is defined by the SerializedFile or its BundleFile
FALLBACK_UNITY_VERSION = "2022.1.3f1"

from os import environ

def is_true_env(name:str, default:str='True'):
    return environ.get(name, default).strip('"').lower() in ('true', '1', 't', 'yes', 'y')

def get_env_int(name:str, default:str|int=0):
    return int(environ.get(name, str(default)).strip('"'))

DEBUG =  is_true_env('DEBUG', 'True') # Toggles debugging branches (useful if memory is exhausted due to errors in typetrees)

# Determines if the TypeTrees for the Object types will be parsed.
#  Disabling this will reduce the load time by a lot (half of the time is spend
#  on parsing the typetrees) but it will also prevent saving some edited files,
#  unless we provide the TypeTrees by ourselves.
SERIALIZED_FILE_PARSE_TYPETREE = is_true_env('SERIALIZED_FILE_PARSE_TYPETREE')

BIG_OBJECT_GUARD = 0 #int(2e9) # 0 or don't try to unpack bigger objects (bytes)

ENABLE_TYPETREEHELPER_FALLBACK = is_true_env('ENABLE_TYPETREEHELPER_FALLBACK') # Fallback to TypeTreeHelper parsing in asset bundles

EXTENDED_SEARCH =  is_true_env('EXTENDED_SEARCH', 'True') # Search all cwd subdirectories for resources

DEBUG_TYPETREES = is_true_env('DEBUG_TYPETREES', 'False') # Toggles TypeTree debugging in ObjectReader and TypeTreeHelper

ENABLE_BINARY_BLOBS = is_true_env('ENABLE_BINARY_BLOBS', 'False') # Enables custom UnityPyBinaryBlob type in TypeTrees

ENABLE_LOGGING_MODULE = get_env_int('ENABLE_LOGGING_MODULE', 0) # 0 = console print; 1 = console log; 2 = file log (default: .\unitypy_log.txt)

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
