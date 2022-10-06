import ffmpegio


ffmpegio.ffmpeg(
    (
        "-y -f lavfi -i testsrc=size=640x480:rate=30:duration=3 "
        "-filter_complex untile=2x1,select=\\'mod(n,2)+1\\':n=2[vout1][vout2] "
        "-map [vout1] sandbox/output1.mp4 "
        "-map [vout2] sandbox/output2.mp4"
    )
)

ffmpegio.ffprobe("sandbox/output2.mp4")
