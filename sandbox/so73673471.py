import ffmpegio


cmd_in = (
    "-f lavfi -i testsrc=size=640x480:rate=30:duration=5 "
    "-f lavfi -i aevalsrc=-2+random(0):duration=5 "
)


tseg = (
    lambda i, t1, t2: rf"[0:v]select=between(t\\,{t1}\\,{t2}),setpts=T-{t1}[v{i+1}];[1:a]aselect=between(t\\,{t1}\\,{t2}),asetpts=T-{t1}[a{i+1}];"
)

cmd = (
    f"{cmd_in} -filter_complex "
    + "".join((tseg(i, i, i + 1) for i in range(3)))
    + (
        r"[v3][a3][v2][a2][v1][a1]concat=n=3:v=1:a=1"  # ;[v2]nullsink;[v3]nullsink;[a2]anullsink;[a3]anullsink
        r" -loglevel debug -y sandbox/out.mp4"
    )
)

ffmpegio.ffmpeg(cmd)
ffmpegio.ffprobe("sandbox/out.mp4")
