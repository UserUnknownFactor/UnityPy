import builtins

DEFAULT_FILE = ".\\unitypy_log.txt"
LOG_FORMAT = "%(asctime)s (%(name)s): %(levelname)s - %(message)s"

NO_COLORAMA = False
try:
    from colorama import Fore, Style, just_fix_windows_console
    just_fix_windows_console()
except:
    NO_COLORAMA = True

from . import config

# NOTE: we use ENABLE_LOGGING_MODULE = 0 to better control 
#             console output since logging only uses full lines
unitypy_logger = None
if config.ENABLE_LOGGING_MODULE:
    import logging
    unitypy_logger = logging.getLogger("UnityPy")
    unitypy_logger.setLevel(logging.DEBUG if config.DEBUG else  logging.INFO)
    if config.ENABLE_LOGGING_MODULE == 2:
        file_handler = logging.FileHandler(DEFAULT_FILE, 'w', encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        for h in unitypy_logger.handlers[:]:
            unitypy_logger.removeHandler(h)
        unitypy_logger.addHandler(file_handler)
    else:
        if not NO_COLORAMA:
            class CustomFormatter(logging.Formatter):
                grey = Style.DIM
                yellow = Fore.YELLOW
                red = Fore.RED
                reset = Style.RESET_ALL
                format = LOG_FORMAT
                FORMATS = {
                    logging.DEBUG: grey + format + reset,
                    logging.INFO: grey + format + reset,
                    logging.WARNING: yellow + format + reset,
                    logging.ERROR: red + format + reset,
                    logging.CRITICAL: bold_red + format + reset
                }
                def format(self, record):
                    log_fmt = self.FORMATS.get(record.levelno, self.format)
                    formatter = logging.Formatter(log_fmt)
                    return formatter.format(record)

            for h in unitypy_logger.handlers[:]:
                unitypy_logger.removeHandler(h)
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(CustomFormatter())
            unitypy_logger.addHandler(stream_handler)

def print_info(text1, text2='', end='\n'):
    """Prints an info text, the first parameter is a dimmed string, the second is a white prefix"""
    if config.ENABLE_LOGGING_MODULE:
        unitypy_logger.info(str(text2) + str(text1))
    else:
        print(str(text2) + str(text1), end=end)

def print_debug(text1, text2='', end='\n'):
    """Prints an info text, the first parameter is a dimmed string, the second is a white prefix"""
    if config.ENABLE_LOGGING_MODULE:
        unitypy_logger.debug(str(text2) + str(text1))
    else:
        if not config.DEBUG: return
        if NO_COLORAMA:
            print(str(text2) + str(text1), end=end)
        else:
            print(str(text2) + (Style.DIM + str(text1) + Style.RESET_ALL), end=end)

def print_error(text1, text2='', end='\n'):
    """Prints an error text, the first parameter is a red string, the second is a white prefix"""
    if config.ENABLE_LOGGING_MODULE:
        unitypy_logger.error(str(text2) + str(text1))
    else:
        if NO_COLORAMA:
            print(str(text2) + str(text1), end=end)
        else:
            print(str(text2) + (Fore.RED + str(text1) + Style.RESET_ALL), end=end)

def print_exception(text1, text2='', end='\n'):
    """Prints an error text, the first parameter is a red string, the second is a white prefix"""
    if config.ENABLE_LOGGING_MODULE:
        unitypy_logger.exception(str(text2) + str(text1))
    else:
        if NO_COLORAMA:
            print(str(text2) + str(text1), end=end)
        else:
            print(str(text2) + (Fore.RED + str(text1) + Style.RESET_ALL), end=end)

def print_warning(text1, text2='', end='\n'):
    """Prints a warning text, the first parameter is a yellow string, the second is a white prefix"""
    if config.ENABLE_LOGGING_MODULE:
        unitypy_logger.warning(str(text2) + str(text1))
    else:
        if NO_COLORAMA:
            print(str(text2) + str(text1), end=end)
        else:
            print(str(text2) + (Fore.YELLOW + str(text1) + Style.RESET_ALL), end=end)

# HACK: This is so we needn't export them in every .py file of the module
builtins.print_info = print_info
builtins.print_debug = print_debug
builtins.print_exception = print_exception
builtins.print_error = print_error
builtins.print_warning = print_warning
