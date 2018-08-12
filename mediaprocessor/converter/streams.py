from abc import ABC
from mediaprocessor.converter.formats import *
import logging
import uuid

log = logging.getLogger(__name__)


class Stream(ABC):
    """
    Generic stream class, it is not to be instantiated directly. Use concrete classes VideoStream, AudioStream and
    SubtitleStream
    """
    # supported_options = []
    kind = ''

    def __init__(self):
        self._options = Options(unique=True)
        self.stream_format = None
        self.supported_options = []
        self._uid = uuid.uuid4()

    @property
    def uid(self):
        return self._uid

    def add_options(self, *_options):
        """Add options to the options pool. Reject options if they are not supported.
        """
        for _opt in _options:
            if _opt.__class__ in self.supported_options and _opt.value is not None:
                self._options.add_option(_opt)
            else:
                log.warning('Option %s was rejected because unsupported by %s', str(_opt),
                            self.__class__.__name__)

    @property
    def options(self):
        return self._options

    def is_duplicate(self, other):
        """Compares streams by comparing the value of options
           attached to them. IMPORTANT: If the option is missing in other, a match will be
           assumed and the comparison will return True. This is a design decision
           so that when building streams from templates, you don't have to specify every single option
           present in a source stream built from a ffprobe."""

        if not isinstance(other, type(self)):
            return False

        if self.stream_format != other.stream_format:
            return False

        for s_opt in self.options.options:
            if not other.options.has_option(s_opt):
                continue
            if not self.options.contains_subset(other.options):
                return False

        return True

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __str__(self):
        output = {self.stream_format.name: {_opt.__class__.__name__: _opt.value for _opt in self.options}}
        return str(output)

    def __hash__(self):
        return hash(self.stream_format.name.__hash__() + self.options.options_no_metadata().__hash__())


class VideoStream(Stream):
    # supported_options = [Codec, PixFmt, Bitrate, Disposition, Height, Width, Level, Profile, Tag, Filter]
    kind = 'video'

    def __init__(self, stream_format):
        assert issubclass(stream_format, VideoFormat)
        super(VideoStream, self).__init__()
        self.stream_format = stream_format
        self.supported_options = stream_format.supported_options.copy()


class AudioStream(Stream):
    # supported_options = [Codec, Channels, Language, Disposition, Bitrate, Tag]
    kind = 'audio'

    def __init__(self, stream_format):
        super(AudioStream, self).__init__()
        assert issubclass(stream_format, AudioFormat)
        self.stream_format = stream_format
        self.supported_options = stream_format.supported_options.copy()


class SubtitleStream(Stream):
    # supported_options = [Codec, Language, Disposition, Tag]
    kind = 'subtitle'

    def __init__(self, stream_format):
        super(SubtitleStream, self).__init__()
        assert issubclass(stream_format, SubtitleFormat)
        self.stream_format = stream_format
        self.supported_options = stream_format.supported_options.copy()


class ImageStream(Stream):
    # supported_options = [Codec, Language, Disposition, Tag]
    kind = 'subtitle'

    def __init__(self, stream_format):
        super(ImageStream, self).__init__()
        assert issubclass(stream_format, ImageFormat)
        self.stream_format = stream_format
        self.supported_options = stream_format.supported_options.copy()


class StreamFactory(object):
    @classmethod
    def create_stream(cls, fmt):
        if issubclass(fmt, VideoFormat):
            return VideoStream(fmt)
        elif issubclass(fmt, AudioFormat):
            return AudioStream(fmt)
        elif issubclass(fmt, SubtitleFormat):
            return SubtitleStream(fmt)
        elif issubclass(fmt, ImageFormat):
            return ImageStream(fmt)
