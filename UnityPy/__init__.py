__version__ = "1.10.11_uuf"

from . import color_logging
from .environment import Environment
from .helpers.ArchiveStorageManager import set_assetbundle_decrypt_key

def load(*args, **kwargs):
    return Environment(*args, fs=None, **kwargs)

# backward compatibility
AssetsManager = Environment
