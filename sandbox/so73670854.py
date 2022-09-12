import ffmpegio
import subprocess as sp

ffmpegio.ffmpeg("-y -f lavfi -i testsrc=size=640x480:rate=30:duration=5 sandbox/in.mp4")

# cmd = "-y -i sandbox/in.mp4 -vf tmix=frames=15:weights=1,fps=30 sandbox/out.mp4"
# cmd = (
#     r"-y -i sandbox/in.mp4 -vf select=\'mod(n,15)+1\':n=15[v0][v1][v2][v3][v4][v5][v6][v7][v8][v9][v10][v11][v12][v13][v14];"
#     "[v0][v1][v2][v3][v4][v5][v6][v7][v8][v9][v10][v11][v12][v13][v14]mix=inputs=15:weights=1 -r 30 sandbox/out.mp4"
# )
# cmd = (
#     r"-y -i sandbox/in.mp4 -vf select=\'mod(n,15)+1\':n=15[v0][v1][v2][v3][v4][v5][v6][v7][v8][v9][v10][v11][v12][v13][v14];"
#     "[v0]setpts=N/30[w0];"
#     "[v1]setpts=N/30[w1];"
#     "[v2]setpts=N/30[w2];"
#     "[v3]setpts=N/30[w3];"
#     "[v4]setpts=N/30[w4];"
#     "[v5]setpts=N/30[w5];"
#     "[v6]setpts=N/30[w6];"
#     "[v7]setpts=N/30[w7];"
#     "[v8]setpts=N/30[w8];"
#     "[v9]setpts=N/30[w9];"
#     "[v10]setpts=N/30[w10];"
#     "[v11]setpts=N/30[w11];"
#     "[v12]setpts=N/30[w12];"
#     "[v13]setpts=N/30[w13];"
#     "[v14]setpts=N/30[w14];"
#     "[w0][w1][w2][w3][w4][w5][w6][w7][w8][w9][w10][w11][w12][w13][w14]mix=inputs=15:weights=1 -r 30 sandbox/out.mp4"
# )
cmd = (
    r"-loglevel debug -y -i sandbox/in.mp4 -vf setpts=\'floor(N/15)/30/TB\',select=\'mod(n,15)+1\':n=15[v0][v1][v2][v3][v4][v5][v6][v7][v8][v9][v10][v11][v12][v13][v14];"
    "[v0][v1][v2][v3][v4][v5][v6][v7][v8][v9][v10][v11][v12][v13][v14]mix=inputs=15:weights=1 -r 30 sandbox/out.mp4"
)

# P = 5

# vlabels = "".join((f"[v{i}]" for i in range(P)))
# wlabels = "".join((f"[w{i}]" for i in range(P)))
# setpts = ";".join((f"[v{i}]setpts=\'N/30*TB\'[w{i}]" for i in range(P)))
# cmd = (
#     rf"-loglevel debug -y -i sandbox/in.mp4 -vf select=\'mod(n,{P})+1\':n={P}{vlabels};"
#     f"{setpts};{wlabels}mix=inputs={P}:weights=1 -r 30 sandbox/out.mp4"
# )

ffmpegio.ffmpeg(cmd)

ffmpegio.ffprobe('sandbox/in.mp4')
ffmpegio.ffprobe('sandbox/out.mp4')

print(cmd)