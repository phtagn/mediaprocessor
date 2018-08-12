from typing import Union, Optional
from mediaprocessor.converter.streams import AudioStream, VideoStream, SubtitleStream, StreamFactory, ImageStream
import logging

log = logging.getLogger(__name__)


class Container(object):
    """
    Container class representing a media file (e.g. avi, mp4, mkv...). A source_container has streams which themselves
    have options. At the moment containers support 3 types of streams, namely video, audio and subtitle.
    """
    supported_formats = ['mp4', 'matroska', 'avi']

    def __init__(self, fmt, file_path=None):
        """

        :param fmt: the format of the source_container, as ffmpeg describes it.
        :type fmt: str
        """
        if fmt in self.supported_formats:
            self.format = fmt
            self.streams = {}
            self.audio_streams = {}
            self.video_streams = {}
            self.subtitle_streams = {}
            self.file_path = file_path
        else:
            raise Exception('Format %s not supported', fmt)

    def add_stream(self, stream: Union[AudioStream, VideoStream, SubtitleStream, ImageStream],
                   stream_number: Optional[int] = None, duplicate_check=False) -> int:
        """
        Adds a stream to the source_container. The stream has to be of a supported type.
        :param stream: The stream to add.
        :type stream: AudioStream, VideoStream or SubtitleStream
        :param stream_number: 0-based number of the stream, in *absolute* terms (i.e. not relative to its type).
        If not supplied, the method will compute the next available stream number.
        :type stream_number: int
        :param duplicate_check: Indicates whether the source_container should check that streams are not duplicated.
        See is_duplicate.
        :type duplicate_check: bool
        :return: Number of the stream that was added, None if the stream was rejected
        :rtype: int or None
        """
        assert isinstance(stream, (VideoStream, AudioStream, SubtitleStream, ImageStream))
        if not duplicate_check or not self.is_duplicate(stream):
            if stream_number is not None:
                sn = stream_number
            else:
                sn = len(self.streams)
            if stream_number in self.streams.keys():
                log.info('Replacing stream %s', stream_number)

            self.streams.update({sn: stream})

            if isinstance(stream, VideoStream):
                self.video_streams.update({stream: len(self.video_streams)})
            elif isinstance(stream, AudioStream):
                self.audio_streams.update({stream: len(self.audio_streams)})
            elif isinstance(stream, SubtitleStream):
                self.subtitle_streams.update({stream: len(self.subtitle_streams)})

            return sn

    def relative_stream_number(self, stream):
        try:
            return self.video_streams[stream]
        except KeyError:
            pass
        try:
            return self.audio_streams[stream]
        except KeyError:
            pass
        try:
            return self.subtitle_streams[stream]
        except KeyError:
            return None

    def absolute_stream_number(self, uid):
        for k, v in self.streams.items():
            if v.uid == uid:
                return k
        return None

    def is_duplicate(self, stream):
        """
        Checks whether a stream is a duplicate of an existing stream already present in the source_container. See __eq__ method
        of Streams class to see how duplicate checking occurs.
        :param stream: Stream to be checked against the source_container
        :type stream: AudioStream, VideoStream or SubtitleStream
        :return: True or False
        :rtype: bool
        """

        if isinstance(stream, AudioStream):
            for k in self.audio_streams:
                if stream == self.audio_streams[k]:
                    return True
        if isinstance(stream, VideoStream):
            for k in self.video_streams:
                if stream.stream_format == self.video_streams[k].stream_format and stream == self.video_streams[k]:
                    return True
        if isinstance(stream, SubtitleStream):
            for k in self.subtitle_streams:
                if stream.stream_format == self.subtitle_streams[k].stream_format and stream == self.subtitle_streams[
                    k]:
                    return True

        return False

    @property
    def hd(self):
        try:
            for s in self.video_streams:
                w = s.options.get_option_by_name('width')
                h = s.options.get_option_by_name('height')

            if (w and w.value >= 1900) or (h and h.value >= 1060):
                return '1080p'
            if (w and w.value >= 1260) or (h and h.value >= 500):
                return '720p'
        except:
            pass
        return 'sd'

    def fix_disposition(self):
        self.set_dispo(self.audio_streams)
        self.set_dispo(self.video_streams)
        self.set_dispo(self.subtitle_streams)

    def set_dispo(self, streams_type):
        from mediaprocessor.converter.options import Disposition
        dispo_dict = {0: [], 1: []}
        for s in streams_type:
            d = s.options.get_unique_option(Disposition)
            if d:
                dispo_dict[d.value].append(s)
            else:
                s.add_options(Disposition({'default': 0}))

        if len(dispo_dict[1]) == 0 and len(dispo_dict[0]) > 0:
            dispo_dict[0][0].add_options(Disposition({'default': 1}))

        if len(dispo_dict[1]) > 1:
            for k in dispo_dict[1][1:]:
                k.add_options(Disposition({'default': 0}))



class ContainerFactory(object):
    """Factory class to build a source_container"""

    @staticmethod
    def container_from_parser(parser) -> Container:
        """
        Builds a source_container from the output of ffprobe. A parser object from the parsers.py
        :param parser: A parser object
        :type parser: mediaprocessor.converter.parsers.FFprobeParser
        :return: a source_container filled with streams
        :rtype: Container
        """

        if 'matroska' in parser.container_format:
            ctn = Container('matroska', parser.file_path)
        elif 'mp4' in parser.container_format:
            ctn = Container('mp4', parser.file_path)
        else:
            ctn = Container(parser.container_format, parser.file_path)

        for idx in range(len(parser.streams)):
            s = StreamFactory.create_stream(parser.stream_format(idx))

            if isinstance(s, VideoStream):
                # v = StreamFactory.create_stream(parser.stream_format(idx))
                s.add_options(parser.pix_fmt(idx),
                              parser.height(idx),
                              parser.width(idx),
                              parser.bitrate(idx),
                              parser.disposition(idx),
                              parser.level(idx),
                              parser.profile(idx))


            elif isinstance(s, AudioStream):
                # a = AudioStream(parser.stream_format(idx))
                s.add_options(parser.channels(idx),
                              parser.language(idx),
                              parser.bitrate(idx),
                              parser.disposition(idx))
                # ctn.add_stream(a, idx)

            elif isinstance(s, SubtitleStream):
                # s = SubtitleStream(parser.stream_format(idx))
                s.add_options(parser.language(idx),
                              parser.disposition(idx))
                # ctn.add_stream(s, idx)

            if s:
                ctn.add_stream(s, idx)
        return ctn
