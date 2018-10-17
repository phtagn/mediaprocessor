from mediaprocessor.converter.containers import Container
from mediaprocessor.converter.options import Language, MetadataOption, Disposition, Filter, Scale, Width, Height
from mediaprocessor.converter.streams import StreamFactory, VideoStream, AudioStream, SubtitleStream
from mediaprocessor.converter.formats import VideoFormat, AudioFormat, SubtitleFormat, ImageFormat
from mediaprocessor.converter.encoders import EncoderFactory
from typing import List
import logging

log = logging.getLogger(__name__)


class OptionBuilder(object):
    """Builds a list of options suitable to pass to subprocess.Popen"""
    image_subtitle_codecs = ['hdmv_pgs_subtitle', 'pgssub']
    bad_audio_codecs = ['truehd']
    bad_codecs = ['truehd', 'mjpeg', 'png']

    def __init__(self, source_container: Container, target_container: Container):
        self.source_container = source_container
        self.target_container = target_container
        self._mapping = list()  # This is the mapping

    @property
    def mapping(self):
        return self._mapping

    def generate_target_container(self, stream_templates, stream_defaults, audio_languages, subtitle_languages,
                                  compare_presets=None):

        for stream in self.source_container.streams:
            index = self.source_container.absolute_stream_number(stream.uid)
            if not stream.stream_format.enabled:
                continue

            ignore = False
            if compare_presets is not None:
                ignore = compare_presets.get(stream.kind, False)

            fmt = stream.stream_format
            if not fmt:
                raise Exception(f'Stream at index {index} has no stream format')

            if isinstance(stream, AudioStream):
                b = False
                for lng in audio_languages:
                    if lng == stream.options.get_unique_option(Language):
                        b = True
                        break

                if not b:
                    continue

            if isinstance(stream, SubtitleStream):
                b = False
                for lng in subtitle_languages:
                    if lng == stream.options.get_unique_option(Language):
                        b = True
                        break

                if not b:
                    continue

            if stream.stream_format in stream_templates:
                # If codec is in the available templates we need to check the options

                target_stream = StreamFactory.create_stream(stream.stream_format)
                if not ignore:
                    incompatible_options = stream.options.incompatible_options(stream_templates[stream.stream_format])
                    target_stream.add_options(*incompatible_options)
                    leftovers = list(filter(lambda x: not incompatible_options.has_option(x), stream.options))
                    target_stream.add_options(*leftovers)
                else:
                    target_stream.add_options(*stream.options)
            else:
                # If it is not, we know we're going to transcode.
                codec, options = stream_defaults[stream.kind]
                target_stream = StreamFactory.create_stream(codec)
                target_stream.add_options(*options)
                leftovers = list(
                    filter(lambda x: not options.has_option(x), stream.options))
                target_stream.add_options(*leftovers)

                # f = Filter()
                # if options.has_option(Height) or options.has_option(Width):
                #     f.add_filter(Scale(ih=stream.options.get_unique_option(Height).value if stream.options.has_option(
                #         Height) else None,
                #                        iw=stream.options.get_unique_option(Width).value if stream.options.has_option(
                #                            Width) else None,
                #                        w=options.get_unique_option(Width).value if options.has_option(Width) else None,
                #                        h=options.get_unique_option(Height).value if options.has_option(Height) else None
                #                        ))
                # target_stream.add_options(f)

            if target_stream.stream_format in stream_templates:
                for opt in stream_templates[target_stream.stream_format]:
                    if isinstance(opt, MetadataOption):
                        target_stream.add_options(opt)

            if isinstance(stream, SubtitleStream):
                # FFmpeg can't transcode from an image based codec into a text based codec.
                if stream.stream_format.is_image is True and target_stream.stream_format.is_image is False:
                    continue

            self.add_mapping(source_index=index, target_stream=target_stream)

    def add_mapping(self, source_index, target_stream, duplicate_check=False):

        try:
            source_stream = self.source_container.streams[source_index]
        except KeyError:
            return None

        assert isinstance(source_stream, target_stream.__class__)
        target_index = self.target_container.add_stream(target_stream, duplicate_check=duplicate_check)

        if target_index is not None:
            self._mapping.append((source_index, target_index))

    @staticmethod
    def print_mapping(source_container, target_container, mapping):
        from io import StringIO
        s = StringIO()
        for m in mapping:
            source_index, target_index = m
            source_stream = source_container.streams[source_index]
            target_stream = target_container.streams[target_index]
            p = f'{source_index} : {source_stream.stream_format.name} -> {target_index}: {target_stream.stream_format.name}\n'
            s.write(p)
            for opt in source_stream.options.options:
                topt = target_stream.options.get_unique_option(opt.__class__)
                if topt:
                    p = f'    {opt} -> {topt}\n'
                else:
                    p = f'    {opt} -> same\n'
                s.write(p)
            s.write('-' * 10 + '\n')

        print(s.getvalue())

    def __str__(self):
        from io import StringIO
        s = StringIO()
        for m in self._mapping:
            source_index, target_index = m
            source_stream = self.source_container.streams[source_index]
            target_stream = self.target_container.streams[target_index]
            p = f'{source_index} : {source_stream.stream_format} -> {target_index}: {target_stream.stream_format}\n'
            s.write(p)
            for opt in source_stream.options.options:
                topt = target_stream.options.get_unique_option(opt.__class__)
                if topt:
                    p = f'    {opt} -> {topt}\n'
                else:
                    p = f'    {opt} -> same\n'
                s.write(p)
            s.write('-' * 10 + '\n')

        return s.getvalue()
