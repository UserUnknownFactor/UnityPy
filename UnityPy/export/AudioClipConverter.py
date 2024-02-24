import ctypes
import os
import platform
from UnityPy.streams import EndianBinaryWriter

# pyfmodex loads the dll/so/dylib on import
# so we have to adjust the environment vars
# before importing it
# This is done in import_pyfmodex()
# which will replace the global pyfmodex var
pyfmodex = None
NO_MODEX = False


def import_pyfmodex():
    global pyfmodex, NO_MODEX
    if pyfmodex is not None or NO_MODEX:
        return

    ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    # determine system - Windows, Darwin, Linux, Android
    system = platform.system()
    if system == "Linux" and "ANDROID_BOOTLOGO" in os.environ:
        system = "Android"
    # determine architecture
    machine = platform.machine()
    arch = platform.architecture()[0]

    if system in ["Windows", "Darwin"]:
        if arch == "32bit":
            arch = "x86"
        elif arch == "64bit":
            arch = "x64"
    elif system == "Linux":
        # Raspberry Pi and Linux on arm projects
        if "arm" in machine:
            if arch == "32bit":
                arch = "armhf" if machine.endswith("l") else "arm"
            elif arch == "64bit":
                # Raise an exception for now; Once it gets supported by FMOD we can just modify the code here
                pyfmodex = None
                raise NotImplementedError(
                    "ARM64 not supported by FMOD.\nUse a 32bit python version."
                )
        elif arch == "32bit":
            arch = "x86"
        elif arch == "64bit":
            arch = "x86_64"
    else:
        pyfmodex = None
        raise NotImplementedError(
            "Couldn't find a correct FMOD library for your system ({system} - {arch})."
        )

    # build path and load library
    LIB_PATH = os.path.join(ROOT, "lib", "FMOD", system, arch)

    # prepare the environment for pyfmodex
    if system == "Windows":
        # register fmod.dll, so that windll.fmod in pyfmodex can find it
        os.environ["PYFMODEX_DLL_PATH"] = os.path.join(LIB_PATH, "fmod.dll")
    else:
        ext = "dylib" if system == "Darwin" else "so"
        os.environ["PYFMODEX_DLL_PATH"] = os.path.join(LIB_PATH, f"libfmod.{ext}")

        # hotfix ctypes for pyfmodex for non windows
        ctypes.windll = getattr(ctypes, "windll", None)

    try:
        import pyfmodex
    except:
        NO_MODEX = True



def extract_audioclip_samples(audio) -> dict:
    """extracts all the samples from an AudioClip
    :param audio: AudioClip
    :type audio: AudioClip
    :return: {filename : sample(bytes)}
    :rtype: dict
    """
    if not audio.m_AudioData:
        # eg. StreamedResource not available
        return {}

    magic = memoryview(audio.m_AudioData)[:8]
    if magic[:4] == b"OggS":
        return {f"{audio.m_Name}.ogg": audio.m_AudioData}
    elif magic[:4] == b"RIFF":
        return {f"{audio.m_Name}.wav": audio.m_AudioData}
    elif magic[4:8] == b"ftyp":
        return {f"{audio.m_Name}.m4a": audio.m_AudioData}
    return dump_samples(audio)


def dump_samples(clip):

    import_pyfmodex()
    if pyfmodex is None or NO_MODEX:
        return {}

    # init system
    system = pyfmodex.System()
    system.init(clip.m_Channels, pyfmodex.flags.INIT_FLAGS.NORMAL, None)

    sound = system.create_sound(
        bytes(clip.m_AudioData),
        pyfmodex.flags.MODE.OPENMEMORY,
        exinfo=pyfmodex.structure_declarations.CREATESOUNDEXINFO(
            length=clip.m_Size,
            numchannels=clip.m_Channels,
            defaultfrequency=clip.m_Frequency,
        ),
    )

    # iterate over subsounds
    samples = {}
    for i in range(sound.num_subsounds):
        if i > 0:
            filename = "%s-%i.wav" % (clip.name, i)
        else:
            filename = "%s.wav" % clip.name
        subsound = sound.get_subsound(i)
        samples[filename] = subsound_to_wav(subsound)
        subsound.release()

    sound.release()
    system.release()
    return samples


def subsound_to_wav(subsound):
    # get sound settings
    length = subsound.get_length(pyfmodex.enums.TIMEUNIT.PCMBYTES)
    channels = subsound.format.channels
    bits = subsound.format.bits
    sample_rate = int(subsound.default_frequency)

    # write to buffer
    writer = EndianBinaryWriter(endian="<")
    # riff chucnk
    writer.write(b"RIFF")
    writer.write_int(length + 36)  # sizeof(FmtChunk) + sizeof(RiffChunk) + length
    writer.write(b"WAVE")
    # fmt chunck
    writer.write(b"fmt ")
    writer.write_int(16)  # sizeof(FmtChunk) - sizeof(RiffChunk)
    writer.write_short(1)
    writer.write_short(channels)
    writer.write_int(sample_rate)
    writer.write_int(sample_rate * channels * bits // 8)
    writer.write_short(channels * bits // 8)
    writer.write_short(bits)
    # data chunck
    writer.write(b"data")
    writer.write_int(length)
    # data
    lock = subsound.lock(0, length)
    for ptr, length in lock:
        ptr_data = ctypes.string_at(ptr, length.value)
        writer.write(ptr_data)
    subsound.unlock(*lock)
    return writer.save()
