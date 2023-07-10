__version__ = "1.10.1"

from .environment import Environment
from .helpers.ArchiveStorageManager import set_assetbundle_decrypt_key


def load(*args, **kwargs):
    return Environment(*args, **kwargs)


# backward compatibility
AssetsManager = Environment
