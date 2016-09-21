Podcast processor configuration files
=====================================

If you’re in a hurry, see the examples below :). They should be reasonably self-explanatory.

The configuration file comprises one or more *segment specifications* that tell the script how to chop up and combine the various podcast input sources. Timestamps are whitespace-delimited (space or newline), but whitespace is otherwise insignificant. Use `#` for comments.

Segment specifications can appear in any order (except for `^` frame inputs, see below), but this will make the file harder to understand. We recommended grouping all segment specifications of the same type in chronological order. Each segment specification starts with an *input specification*, followed by zero or more *time specifications*.


Input specifications
--------------------

These are of the form: `[type:filename:num]` (the `[ ]` are delimiters)

`type` is mandatory, and must be one of `a`/`audio`, `v`/`video`, or `f`/`frame`. Audio and video inputs are self-explanatory. Frame inputs are special type of video input based on a single still image, which could be from a JPEG image (preferred), or automatically extracted from a video source or PDF. You need to specify a frame number for the latter (see below).

`filename` is mandatory for frame inputs. The special filename `^` indicates that the frame is to be extracted from the immediately preceding segment, so segment order within the configuration file is important for these. If you’ve specified default input files using `--audio` or `--video` on the command line, you can omit `filename` for audio and video inputs (as appropriate), and the script will use the default inputs. If there are no default input files specified, or you want to input from a file other than the default, then `filename` is required.

`num` is optional and represents either the `ffmpeg` stream number for audio and video inputs, or the frame/page number for frame inputs. It is zero-indexed (so page 1 of a PDF input is specified as 0). It defaults to 0 if omitted. For frame inputs, you can also specify `-1` or `last` to indicate that it should use the last frame of the input file (negative values other than -1 are currently not supported).


Time specifications
-------------------

These are normally just a sequence of timestamps, representing punch in and punch out times. Timestamps are in `hh:mm:ss.fff` format. Seconds (`ss`) are the only required component. Components can have any number of digits, but the fractional part (`fff`) is truncated to millisecond resolution. This provides considerable flexibility in specifying times, e.g., you can specify 90 minutes as `1:30:00`, `90:00`, or even just `5400`. The punch out time for a segment *must* be later than the punch in time, but otherwise you can list timestamps in any order. However, we recommend listing them chronologically for the sake of sanity!

If you provide no timestamps, then the script will generate one segment punching in at 0 and punching out at the end of the input. If you provide an even number of timestamps, each pair of timestamps (*t₁*, *t₂*) will generate a new segment punching in at *t₁* and punching out at *t₂*. If you provide an odd number of timestamps, each pair of timestamps will generate segments as above, plus one final segment punching in at the last timestamp and punching out at the end of the input.

As frame inputs are a still image, the punch in and punch out timestamps effectively determine the duration of the generated frame (i.e., punch out minus punch in). It’d be unusual to specify more than two timestamps for a single frame, but if you need to generate multiple versions of the same frame with different durations, this should work as expected.

You can also use the special sequence `@filename` to generate a punch out point based on the duration (not the content!) of the specified file. This should either be the only entry (implying punch in at 0, punch out after file duration), or preceded by *exactly one* timestamp (implying punch in at timestamp, punch out at timestamp + file duration). This is handy if you want to do something like insert a filler frame that matches the duration of an audio file.

The punch in/out times for corresponding segments in the audio and video streams don’t have to match (this would only occur when the audio and video inputs come from the same file), but the total duration of the audio stream should match that of the video stream if both are included.


Examples
--------

These illustrate some common use cases. Some have been tested, but not all!


```
# Read the entire video and audio input (defaults).

[a]
[v]
```

```
# Segment the video and audio, skipping irrelevant parts at the start and
# end, and five minutes in the middle.

[a] 1:35 25:00 30:00 54:27
[v] 0:17 23:42 28:42 53:09
```

```
# Split audio into two segments separated by an audio segment from
# filler.wav. Split video into two corresponding segments, separated
# by a filler frame generated by repeating the last frame of the first
# video segment for the same duration as filler.wav.

[a] 1:53 23:15
[a:filler.wav]
[a] 49:42 50:25

[v] 2:15 23:37
[f:^:last] @filler.wav
[v] 50:04 50:47
```

```
# Stitch a collection of individual JPEG slide images together with the
# recorded audio. Notice that the four times for the audio correspond
# to the punch in time of the first frame, the punch out time of the
# second-last frame, the punch in time of the last frame, and the punch
# out time of the last frame, respectively.

[a:audio.wav] 7:59 25:50 53:00 53:27
[f:slide-000.jpg] 7:59 8:46
[f:slide-001.jpg] 8:46 10:28
[f:slide-002.jpg] 10:28 12:19
[f:slide-003.jpg] 12:19 13:53
[f:slide-004.jpg] 13:53 14:26
[f:slide-005.jpg] 14:26 16:22
[f:slide-006.jpg] 16:22 20:16
[f:slide-007.jpg] 20:16 20:50
[f:slide-008.jpg] 20:50 22:32
[f:slide-009.jpg] 22:32 22:49
[f:slide-010.jpg] 22:49 25:59
[f:slide-011.jpg] 25:59 26:25
[f:slide-012.jpg] 26:25 25:50
[f:slide-013.jpg] 53:00 53:27
```

```
# Extract slide images from a PDF and merge with the recorded audio.

[a] 0:04 26:33
[f:slides.pdf:0] 0:04 3:39
[f:slides.pdf:1] 3:39 9:14
[f:slides.pdf:2] 9:14 13:58
[f:slides.pdf:3] 13:58 17:05
[f:slides.pdf:4] 17:05 17:13
[f:slides.pdf:5] 17:13 17:22
[f:slides.pdf:6] 17:22 17:28
[f:slides.pdf:7] 17:28 21:25
[f:slides.pdf:8] 21:25 24:04
[f:slides.pdf:9] 24:04 24:07
[f:slides.pdf:10] 24:07 26:17
[f:slides.pdf:11] 26:17 26:33
```

```
# The poor man's text overlay :). If you make a mistake and want to
# include a correction, you can just pull the relevant slide from the
# original PDF, annotate it as necessary, then insert that at the
# appropriate point in the final render. You could also use a similar
# technique to insert new audio, although that'll be trickier to get
# the timing right.

[a] 06:39 33:42
[a:joiner.wav]
[a] 54:01 54:12

[v] 03:36 28:52
[f:slide_11.pdf:0] 28:52 29:02
[v] 29:02 30:39
[f:^:last] @joiner.wav
[v] 50:58 51:09
```
