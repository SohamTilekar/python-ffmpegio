import subprocess
import ffmpegio


ffmpegio.ffmpeg(
    "-y -f lavfi -i testsrc=size=640x480:rate=30:duration=3 sandbox/in.mp4"
)

bytes = ffmpegio.ffmpeg(
    [
        "-i",
        "sandbox/in.mp4",
        "-ss",
        "00:00:01",
        "-vf",
        "scale=200:220",
        "-vframes",
        "1",
        "-f","image2pipe",
        "-c","mjpeg",
        "-",
    ],
    stdout=subprocess.PIPE,
).stdout

with open('sandbox/out1.jpg','wb') as f:
        f.write(bytes)
