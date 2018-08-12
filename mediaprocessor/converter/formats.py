from mediaprocessor.converter.options import *
import logging

log = logging.getLogger(__name__)


class BaseFormat(object):
    name = ''
    supported_options = []
    score = 0
    enabled = True


class VideoFormat(BaseFormat):
    supported_options = [PixFmt, Bitrate, Disposition, Height, Width, Level, Profile, Tag, Filter]


class AudioFormat(BaseFormat):
    supported_options = [Channels, Language, Disposition, Bitrate, Tag]


class SubtitleFormat(BaseFormat):
    supported_options = [Language, Disposition, Tag]
    is_image = False


class ImageFormat(BaseFormat):
    enabled = False


class TheoraFormat(VideoFormat):
    name = 'theora'


class DivxFormat(VideoFormat):
    name = 'divx'


class Vp8Format(VideoFormat):
    name = 'vp8'


class H263Format(VideoFormat):
    name = 'h263'


class FlvFormat(VideoFormat):
    name = 'flv'


class Mpeg1Format(VideoFormat):
    name = 'mpeg1'


class Mpeg2Format(VideoFormat):
    name = 'mpeg2'


class H264Format(VideoFormat):
    supported_options = VideoFormat.supported_options.copy()
    supported_options.extend([Profile, Level])
    name = 'h264'


class HevcFormat(VideoFormat):
    supported_options = VideoFormat.supported_options.copy()
    supported_options.extend([Profile, Level])
    name = 'hevc'


class VorbisFormat(AudioFormat):
    name = 'vorbis'


class Mp3Format(AudioFormat):
    name = 'mp3'


class Mp2Format(AudioFormat):
    name = 'mp2'


class Eac3Format(AudioFormat):
    name = 'eac3'
    score = 2


class Ac3Format(AudioFormat):
    name = 'ac3'
    score = 1


class DtsFormat(AudioFormat):
    name = 'dts'
    score = 3


class FlacFormat(AudioFormat):
    name = 'flac'
    score = 3


class AacFormat(AudioFormat):
    name = 'aac'
    score = 1


class TrueHDFormat(AudioFormat):
    name = 'truehd'
    score = 5
    enabled = False


class MovtextFormat(SubtitleFormat):
    name = 'mov_text'


class SrtFormat(SubtitleFormat):
    name = 'srt'


class SSAFormat(SubtitleFormat):
    name = 'ssa'


class SubRipFormat(SubtitleFormat):
    name = 'subrip'


class DvdSubFormat(SubtitleFormat):
    name = 'dvdsub'
    is_image = True


class DVBSubFormat(SubtitleFormat):
    name = 'dvbsub'
    is_image = True


class WebVTTFormat(SubtitleFormat):
    name = 'webvtt'


class PgsFormat(SubtitleFormat):
    name = 'hdmv_pgs_subtitle'
    is_image = True


class PngFormat(ImageFormat):
    name = 'png'


class MjpegFormat(ImageFormat):
    name = 'mjpeg'


class FormatFactory(object):
    supported_formats = {
        'theora': TheoraFormat,
        'h264': H264Format,
        # 'x264': H264Format,  # Alias
        # 'h265': HevcFormat,
        'hevc': HevcFormat,
        'divx': DivxFormat,
        'vp8': Vp8Format,
        'h263': H263Format,
        'flv': FlvFormat,
        'mpeg1': Mpeg1Format,
        'mpeg2': Mpeg2Format,

        'vorbis': VorbisFormat,
        'aac': AacFormat,
        'mp3': Mp3Format,
        'mp2': Mp2Format,
        'ac3': Ac3Format,
        'eac3': Eac3Format,
        'dts': DtsFormat,
        'flac': FlacFormat,

        'mov_text': MovtextFormat,
        'srt': SrtFormat,
        'ssa': SSAFormat,
        'ass': SSAFormat,
        'subrip': SubRipFormat,
        'dvdsub': DvdSubFormat,
        'dvbsub': DVBSubFormat,
        'webvtt': WebVTTFormat,
        'hdmv_pgs_subtitle': PgsFormat,
        'pgs': PgsFormat,

        'png': PngFormat,
        'mjpeg': MjpegFormat
    }

    @classmethod
    def get_format(cls, fmt):
        try:
            return cls.supported_formats[fmt.lower()]
        except KeyError:
            return None
