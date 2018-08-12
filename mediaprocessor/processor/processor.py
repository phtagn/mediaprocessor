from mediaprocessor.configuration_mod import configuration
from mediaprocessor.converter.optionbuilder import OptionBuilder
from mediaprocessor.converter.containers import ContainerFactory, Container
from mediaprocessor.converter.streams import AudioStream
from mediaprocessor.converter.options import *
from mediaprocessor.converter.encoders import EncoderFactory, Encoders
from mediaprocessor.converter.formats import FormatFactory
import sys
import logging
from mediaprocessor.converter.ffmpeg import FFMpeg, FFMpegError, FFMpegConvertError

log = logging.getLogger()
log.setLevel(logging.DEBUG)
sh = logging.StreamHandler(sys.stdout)
sh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s - %(message)s')
sh.setFormatter(formatter)
log.addHandler(sh)

# log = logging.getLogger(__name__)

"""Processes a video file in steps:
1) Analyse video file
2) Assess appropriate streams from options
3) Build templates from options
4) Build option list
5) Convert !
"""


class ProcessorConfig(object):
    def __init__(self, config, target):
        self.config = config
        self.target = target

        self._audio_languages = [Language(lng) for lng in self.config['Languages']['audio']]
        self._subtitle_languages = [Language(lng) for lng in self.config['Languages']['subtitle']]

        self.ffmpeg = FFMpeg(self.config['FFMPEG']['ffmpeg'], self.config['FFMPEG']['ffprobe'])
        self.ignore = {'video': self.config['Containers'][self.target]['video'].get('prefer_copy', False),
                       'audio': self.config['Containers'][self.target]['audio'].get('prefer_copy', False),
                       'subtitle': self.config['Containers'][self.target]['subtitle'].get('prefer_copy', False)}

        self.audio_create_tracks = [FormatFactory.get_format(fmt)
                                    for fmt in
                                    self.config['Containers'][self.target]['audio']['force_create_tracks'] if fmt]

        self._defaults = self.load_defaults()
        self.program_encoders = Encoders(self.ffmpeg)
        self._stream_formats = self.load_stream_formats()
        self.encoders_defaults = self.load_encoders()
        self.preferred_encoders = self.config['PreferredEncoders']
        self.encoder_factory = EncoderFactory(self.program_encoders, self.encoders_defaults, self.preferred_encoders)
        self.preopts = self.config['Containers'][self.target]['preopts']
        self.postopts = self.config['Containers'][self.target]['postopts']

    @property
    def defaults(self):
        return self._defaults

    @property
    def stream_formats(self):
        return self._stream_formats

    @property
    def audio_languages(self):
        return self._audio_languages

    @property
    def subtitle_languages(self):
        return self._subtitle_languages

    def load_defaults(self):
        defaults = {}
        for k in ['audio', 'video', 'subtitle']:
            _options = Options()

            try:
                str_format = self.config['Containers'][self.target][k]['default_format']
                fmt = FormatFactory.get_format(str_format)
            except IndexError:
                log.critical('There are no default options in accepted_track_formats')
                raise Exception('No default options')

            if str_format in self.config['StreamFormats']:
                fmt = FormatFactory.get_format(str_format)
                for opt_name, opt_value in self.config['StreamFormats'][fmt.name].items():
                    option = OptionFactory.get_option(opt_name)
                    if option:
                        if isinstance(opt_value, list) and len(opt_value) > 0:
                            _options.add_option(option(opt_value[0]))
                        else:
                            _options.add_option(option(opt_value))

            if _options:
                defaults.update({k: (fmt, _options)})

        return defaults

    def load_stream_formats(self):

        templates = {}
        for k in ['video', 'audio', 'subtitle']:

            for str_format in self.config['Containers'][self.target][k].get('accepted_track_formats', []):
                fmt = FormatFactory.get_format(str_format)
                if fmt.name in self.config['StreamFormats']:
                    _options = Options()

                    for opt_name, opt_value in self.config['StreamFormats'][fmt.name].items():
                        option = OptionFactory.get_option(opt_name)
                        if option:
                            if isinstance(opt_value, list):
                                for v in opt_value:
                                    _options.add_option(option(v))
                            else:
                                _options.add_option(option(opt_value))
                    templates.update({fmt: _options})

        return templates

    def load_encoders(self):

        encs = {}

        for encoder in self.program_encoders.supported_codecs:

            _options = Options()
            if encoder.codec_name in self.config['EncoderOptions']:
                for k, v in self.config['EncoderOptions'][encoder.codec_name].items():
                    _option = OptionFactory.get_option(k)
                    if _option:
                        _options.add_option(_option(v))

            encs[encoder.codec_name] = _options

        return encs


class Processor(object):

    def __init__(self, config, input_file, output_file, target):
        """
        Creates a target source_container from the inputfile, taking into account the configuration
        :param config: a configuration object
        :type config: ConfigObj
        :param input_file: path to the input file
        :type input_file: os.path.abspath
        :param target: the target source_container to create
        :type target: str
        """
        self.config = ProcessorConfig(config, target)
        if os.path.exists(input_file):
            self.infile = input_file
        else:
            raise FileNotFoundError

        self.source_container = ContainerFactory.container_from_parser(self.config.ffmpeg.probe(self.infile))

        self.target_container = Container(target, output_file)

        self.output = output_file
        self.options = []

        self.ob = OptionBuilder(self.source_container, self.target_container)

    def process(self):

        self.ob.generate_target_container(self.config.stream_formats,
                                          self.config.defaults,
                                          self.config.audio_languages,
                                          self.config.subtitle_languages,
                                          compare_presets=self.config.ignore)

        self.add_extra_streams()
        #        self.add_extra_audio_streams()
        self.target_container.fix_disposition()
        self.ob.print_mapping(self.source_container, self.target_container, self.ob.mapping)
        commandline = self.config.ffmpeg.generate_commands(self.source_container,
                                                           self.target_container,
                                                           self.ob.mapping,
                                                           self.config.encoder_factory,
                                                           preopts=self.config.preopts,
                                                           postopts=self.config.postopts)

        log.debug('FFmpeg command:\n %s', ' '.join(commandline))

        try:
            for p in self.config.ffmpeg.convert2(commandline):
                print(p)

            return self.target_container
        except (FFMpegError, FFMpegConvertError):
            return None

    def suitable_language(self, stream):

        if stream.options.get_unique_option(Language) in self.config.audio_languages:
            return True
        return False

    def add_extra_streams(self):
        # This is actually awfully difficult...
        few_audio_tracks = True
        tpl = self.config.stream_formats

        # Step 1, determine if we need to create extra streams and load options accordingly
        extra_streams = []
        for fmt in self.config.audio_create_tracks:
            stream = AudioStream(fmt)
            if fmt in tpl:
                stream.add_options(*tpl[fmt].options)
                extra_streams.append(stream)

        # Identify how many different input audio streams we have.
        # If few_audio_tracks is True, streams will be considered different if their language is different, regardless
        # of the other options. This means that an AAC track in English and an AC3 track in English will be
        # considered the same.
        # If few_audio_tracks is False, streams will be considered different if any of their options are different.
        # Therefore, an AAC track in English and an AC3 track in English will be considered different.

        # Select source candidates, where we take the "best" source to create our extra tracks.
        # The best source is that whose a) Codec is best rated, b) has the most channels c) has the highest bitrate.:
        if few_audio_tracks:
            candidates = []
            for lng in self.config.audio_languages:
                ok_audio_streams = filter(lambda s: s.options.get_unique_option(Language) == lng,
                                          self.source_container.audio_streams)
                if ok_audio_streams:
                    m = sorted(ok_audio_streams,
                               key=lambda s: (s.stream_format.score,
                                              s.options.get_unique_option(Channels).value,
                                              s.options.get_unique_option(Bitrate)), reverse=True)
                    candidates.append(m[0])
        else:
            candidates = self.source_container.audio_streams

            # Step 2, check if stream is acceptable. An extra audio stream should not be created if:
            # a) All options are the same as another stream except metadata and bitrate
            # b) The number of channels is higher than that of the source stream

        for s in candidates:
            for t in extra_streams:
                # 1) Create target stream and populate with options.
                target_stream = AudioStream(t.stream_format)
                target_stream.add_options(*t.options)
                leftovers = list(filter(lambda x: not target_stream.options.has_option(x), s.options))
                target_stream.add_options(*leftovers)

                # 2) A few quick checks:
                if (s.stream_format == t.stream_format and
                        s.options.get_unique_option(Bitrate) < target_stream.options.get_unique_option(Bitrate)):
                    # We don't create target streams that have the same stream format but a higher bitrate
                    # as we can't create bits out of thin air.
                    continue
                if (s.stream_format == t.stream_format and
                        s.options.get_unique_option(Channels) < target_stream.options.get_unique_option(Channels)):
                    # We don't create the same format where the target has more channels than the source.
                    continue

                # Now we need to iterate over all audio streams to check if there isn't
                # a better stream available already.
                b = True
                for o in self.source_container.audio_streams:
                    if o.options.get_unique_option(Language) != target_stream.options.get_unique_option(Language):
                        continue
                    if o == target_stream:
                        b = False
                    if (few_audio_tracks and (o.stream_format == target_stream.stream_format and
                                              o.options.get_unique_option(Bitrate) > target_stream.options.get_unique_option(Bitrate))
                    ):
                        b = False
                if b:
                    index = self.source_container.absolute_stream_number(s.uid)
                    self.ob.add_mapping(index, target_stream, False)

                # self.ob.add_mapping(idx, target_stream, duplicate_check=True)

        # if an option is defined, keep it, otherwise replace with source_stream option

        # Step 3 - Identify best source stream for creation

    def add_extra_audio_streams(self):

        tpl = self.config.stream_formats

        extra_streams = []
        for fmt in self.config.audio_create_tracks:
            stream = AudioStream(fmt)
            if fmt in tpl:
                stream.add_options(*tpl[fmt].options)
                extra_streams.append(stream)

        if extra_streams:
            for idx, stream in self.source_container.streams.items():
                if isinstance(stream, AudioStream):
                    if isinstance(stream, AudioStream):
                        b = False
                        for lng in self.config.audio_languages:
                            if lng == stream.options.get_unique_option(Language):
                                b = True
                                break

                        if not b:
                            continue

                    for t in extra_streams:
                        target_stream = AudioStream(t.stream_format)
                        target_stream.add_options(*t.options)
                        leftovers = list(filter(lambda x: not target_stream.options.has_option(x), stream.options))
                        target_stream.add_options(*leftovers)
                        self.ob.add_mapping(idx, target_stream, duplicate_check=True)

    def convert(self):
        try:
            for t in self.config.ffmpeg.convert(self.infile, self.output, self.options):
                log.debug(t)
            return self.output

        except:
            return None


if __name__ == '__main__':
    import os

    laptop = os.path.abspath('/Users/Jon/Downloads/Ratatouille (2007) - HD 1080P.mp4')
    desktop = os.path.abspath("//Users/Jon/Downloads/Geostorm 2017 1080p FR EN X264 AC3-mHDgz.mkv")
    cfgmgr = configuration.CfgMgr()
    cfgmgr.load('defaults.ini')
    p = Processor(cfgmgr.cfg, desktop, '/Users/jon/Downloads/toto.mp4', 'mp4')
    p.process()
#    p.convert()
