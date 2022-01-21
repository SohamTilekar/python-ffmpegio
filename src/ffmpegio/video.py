import numpy as np

from . import ffmpegprocess, utils, configure, FFmpegError, probe
from .utils import filter as filter_utils, log as log_utils


def _run_read(
    *args, shape=None, pix_fmt_in=None, r_in=None, s_in=None, show_log=None, **kwargs
):
    """run FFmpeg and retrieve audio stream data
    :param *args ffmpegprocess.run arguments
    :type *args: tuple
    :param shape: output frame size if known, defaults to None
    :type shape: (int, int), optional
    :param pix_fmt_in: input pixel format if known but not specified in the ffmpeg arg dict, defaults to None
    :type pix_fmt_in: str, optional
    :param s_in: input frame size (wxh) if known but not specified in the ffmpeg arg dict, defaults to None
    :type s_in: str or (int, int), optional
    :param show_log: True to show FFmpeg log messages on the console,
                     defaults to None (no show/capture)
                     Ignored if stream format must be retrieved automatically.
    :type show_log: bool, optional
    :param **kwargs ffmpegprocess.run keyword arguments
    :type **kwargs: tuple
    :return: image data
    :rtype: numpy.ndarray
    """

    dtype, shape, r = configure.finalize_video_read_opts(
        args[0], pix_fmt_in, s_in, r_in
    )

    if shape is None or r is None:
        configure.clear_loglevel(args[0])

        out = ffmpegprocess.run(*args, capture_log=True, **kwargs)
        if out.returncode:
            raise FFmpegError(out.stderr)

        info = log_utils.extract_output_stream(out.stderr)
        dtype, ncomp, _ = utils.get_video_format(info["pix_fmt"])
        shape = (-1, *info["s"][::-1], ncomp)
        r = info["r"]

        data = np.frombuffer(out.stdout, dtype).reshape(*shape)
    else:
        out = ffmpegprocess.run(
            *args,
            dtype=dtype,
            shape=shape,
            capture_log=False if show_log else True,
            **kwargs,
        )
        if out.returncode:
            raise FFmpegError(out.stderr)
        data = out.stdout
    return r, data


def create(
    expr,
    *args,
    t_in=None,
    pix_fmt=None,
    vf=None,
    progress=None,
    show_log=None,
    **kwargs,
):
    """Create a video using a source video filter

    :param expr: name of the source filter
    :type expr: str
    :param \\*args: filter arguments
    :type \\*args: tuple, optional
    :param duration:
    :type duration: int
    :param progress: progress callback function, defaults to None
    :type progress: callable object, optional
    :param show_log: True to show FFmpeg log messages on the console,
                     defaults to None (no show/capture)
                     Ignored if stream format must be retrieved automatically.
    :type show_log: bool, optional
    :param \\**options: filter keyword arguments
    :type \\**options: dict, optional
    :return: video data
    :rtype: numpy.ndarray

    Supported Video Source Filters
    ------------------------------

    =============  ==============================================================================
    filter name    description
    =============  ==============================================================================
    "color"        uniformly colored frame
    "allrgb"       frames of size 4096x4096 of all rgb colors
    "allyuv"       frames of size 4096x4096 of all yuv colors
    "gradients"    several gradients
    "mandelbrot"   Mandelbrot set fractal
    "mptestsrc"    various test patterns of the MPlayer test filter
    "life"         life pattern based on John Conway’s life game
    "haldclutsrc"  identity Hald CLUT
    "testsrc"      test video pattern, showing a color pattern
    "testsrc2"     another test video pattern, showing a color pattern
    "rgbtestsrc"   RGB test pattern useful for detecting RGB vs BGR issues
    "smptebars"    color bars pattern, based on the SMPTE Engineering Guideline EG 1-1990
    "smptehdbars"  color bars pattern, based on the SMPTE RP 219-2002
    "pal100bars"   a color bars pattern, based on EBU PAL recommendations with 100% color levels
    "pal75bars"    a color bars pattern, based on EBU PAL recommendations with 75% color levels
    "yuvtestsrc"   YUV test pattern. You should see a y, cb and cr stripe from top to bottom
    "sierpinski"   Sierpinski carpet/triangle fractal
    =============  ==============================================================================

    https://ffmpeg.org/ffmpeg-filters.html#Video-Sources

    """

    url, (r_in, s_in) = filter_utils.compose_source("video", expr, *args, **kwargs)

    need_t = ("mandelbrot", "life")
    if t_in is None and any((expr.startswith(f) for f in need_t)):
        raise ValueError(f"Some sources {need_t} must have t_in specified")

    ffmpeg_args = configure.empty()
    inopts = configure.add_url(ffmpeg_args, "input", url, {"f": "lavfi"})[1][1]
    outopts = configure.add_url(ffmpeg_args, "output", "-", {})[1][1]

    if t_in is not None:
        inopts["t"] = t_in

    for k, v in zip(
        ("pix_fmt", "filter:v"),
        (pix_fmt or "rgb24", vf),
    ):
        if v is not None:
            outopts[k] = v

    return _run_read(
        ffmpeg_args, progress=progress, r_in=r_in, s_in=s_in, show_log=show_log
    )


def read(url, progress=None, show_log=None, **options):
    """Read video frames

    :param url: URL of the video file to read.
    :type url: str
    :param vframes: number of frames to read, default to None. If not set,
                    uses the timing options to determine the number of frames.
    :type vframes: int, optional
    :param stream_id: video stream id (numeric part of ``v:#`` specifier), defaults to 0.
    :type stream_id: int, optional
    :param progress: progress callback function, defaults to None
    :type progress: callable object, optional
    :param show_log: True to show FFmpeg log messages on the console,
                     defaults to None (no show/capture)
                     Ignored if stream format must be retrieved automatically.
    :type show_log: bool, optional
    :param \\**options: other keyword options (see :doc:`options`)
    :type \\**options: dict, optional

    :return: frame rate and video frame data (dims: time x rows x cols x pix_comps)
    :rtype: (`fractions.Fraction`, `numpy.ndarray`)
    """

    pix_fmt = options.get("pix_fmt", None)

    # get pix_fmt of the input file only if needed
    if pix_fmt is None and "pix_fmt_in" not in options:
        info = probe.video_streams_basic(url, 0)[0]
        pix_fmt_in = info["pix_fmt"]
        s_in = (info["width"], info["height"])
        r_in = info["frame_rate"]
    else:
        pix_fmt_in = s_in = r_in = None

    # get url/file stream
    url, stdin, input = configure.check_url(url, False)

    input_options = utils.pop_extra_options(options, "_in")

    ffmpeg_args = configure.empty()
    configure.add_url(ffmpeg_args, "input", url, input_options)
    configure.add_url(ffmpeg_args, "output", "-", options)

    return _run_read(
        ffmpeg_args,
        stdin=stdin,
        input=input,
        progress=progress,
        show_log=show_log,
        pix_fmt_in=pix_fmt_in,
        s_in=s_in,
        r_in=r_in,
    )


def write(url, rate, data, show_log=None, progress=None, **options):
    """Write Numpy array to a video file

    :param url: URL of the video file to write.
    :type url: str
    :param rate: frame rate in frames/second
    :type rate: `float`, `int`, or `fractions.Fraction`
    :param data: video frame data 4-D array (frame x rows x cols x components)
    :type data: `numpy.ndarray`
    :param progress: progress callback function, defaults to None
    :type progress: callable object, optional
    :param show_log: True to show FFmpeg log messages on the console,
                     defaults to None (no show/capture)
    :type show_log: bool, optional
    :param \\**options: other keyword options (see :doc:`options`)
    :type \\**options: dict, optional
    """

    url, stdout, _ = configure.check_url(url, True)

    input_options = utils.pop_extra_options(options, "_in")

    ffmpeg_args = configure.empty()
    configure.add_url(
        ffmpeg_args,
        "input",
        *utils.array_to_video_input(rate, data=data, **input_options),
    )
    configure.add_url(ffmpeg_args, "output", url, options)

    ffmpegprocess.run(
        ffmpeg_args,
        input=data,
        stdout=stdout,
        progress=progress,
        capture_log=False if show_log else None,
    )


def filter(expr, rate, input, progress=None, **options):
    """Filter video frames.

    :param expr: SISO filter graph.
    :type expr: str
    :param rate: input frame rate in frames/second
    :type rate: `float`, `int`, or `fractions.Fraction`
    :param input: input image data
    :type input: 2D/3D numpy.ndarray
    :param progress: progress callback function, defaults to None
    :type progress: callable object, optional
    :return: output sampling rate and data
    :rtype: numpy.ndarray

    """

    input_options = utils.pop_extra_options(options, "_in")

    ffmpeg_args = configure.empty()
    configure.add_url(
        ffmpeg_args,
        "input",
        *utils.array_to_video_input(rate, data=input, **input_options),
    )
    outopts = configure.add_url(ffmpeg_args, "output", "-", options)[1][1]
    outopts["filter:v"] = expr

    return _run_read(
        ffmpeg_args,
        input=input,
        progress=progress,
        show_log=True,
    )
