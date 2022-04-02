import logging, os
from ffmpegio.plugins.devices import dshow
from ffmpegio.path import FFMPEG_VER
from ffmpegio import devices
from packaging.version import Version
import pytest


@pytest.mark.skipif(os.name != "nt", reason="only run on windows")
def test_dshow():
    if FFMPEG_VER >= Version("5.0"):
        devices.scan()
        devs = devices.SOURCES["dshow"]["list"]
    else:
        devs = dshow._scan()
    for _, spec in devs.items():
        print(dshow._resolve([spec]))
        print(dshow._list_options(spec))
    if devs:
        print(dshow._resolve([dev for dev in devs.values()]))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    import ffmpegio

    # if ffmpegio.path.FFMPEG_VER!='5.0':
    #     v5 = r"C:\Users\tikuma\AppData\Local\Programs\ffmpeg-5.0\bin"
    #     ffmpegio.set_path(fr"{v5}\ffmpeg.exe", fr"{v5}\ffprobe.exe")
    #     print(ffmpegio.path.FFMPEG_VER)

    print(os.name)
    test_dshow()