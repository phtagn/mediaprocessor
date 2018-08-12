import unittest
from mediaprocessor.converter.options import *
from mediaprocessor.converter.parsers import FFprobeParser
from mediaprocessor.converter.formats import FormatFactory

class TestOptionFactory(unittest.TestCase):
    def test_get_option(self):
        self.assertIsNone(OptionFactory.get_option('NonExistent'))
        self.assertIs(OptionFactory.get_option('codec'), Codec)

    def test_streamvalueoptions(self):
        opt1 = Bitrate(1000)
        opt2 = Bitrate(1001)
        self.assertGreater(opt2, opt1)

    def test_options(self):
        options = Options(unique=True)
        options.add_option(Codec)


class TestFFprobeParser(unittest.TestCase):
    def setUp(self):
        with open('output.json', 'r') as infile:
            self.input = infile.read()

    def test_parser(self):

        parser = FFprobeParser(self.input)

        self.assertEqual(parser.container_format, 'matroska,webm')
        self.assertEqual(parser.file_path, '/Users/Jon/Downloads/Geostorm 2017 1080p FR EN X264 AC3-mHDgz.mkv')
        # Stream 0, video stream
        self.assertEqual(parser.stream_format(0), FormatFactory.get_format('h264'))
        self.assertEqual(parser.pix_fmt(0), PixFmt('yuv420p'))
        self.assertEqual(parser.bitrate(0), Bitrate(2052))
        self.assertEqual(parser.profile(0), Profile('High'))
        self.assertEqual(parser.level(0), Level(4.0))
        self.assertEqual(parser.height(0), Height(800))
        self.assertEqual(parser.width(0), Width(1920))

        # self.assertEqual(parser.disposition(0), Disposition(1))
        # Stream 1, audio stream
        self.assertEqual(parser.stream_format(1), FormatFactory.get_format('ac3'))
        self.assertEqual(parser.bitrate(1), Bitrate(384))
        self.assertEqual(parser.channels(1), Channels(6))
        self.assertEqual(parser.language(1), Language('fre'))

        self.assertEqual(parser.stream_format(2), FormatFactory.get_format('ac3'))
        self.assertEqual(parser.stream_format(3), FormatFactory.get_format('aac'))
        self.assertEqual(parser.stream_format(4), FormatFactory.get_format('ass'))


class TestOptions(unittest.TestCase):
    def setUp(self):
        options_unique = Options(True)
        options_not_unique = Options()

        options_unique.add_option(PixFmt('yuv240p'))
        #options_unique.add_option()

    def test_compare(self):
        # Test options evaluate correctly regardless of order
        o1 = Options(unique=True)
        o2 = Options(unique=True)
        o1.add_option(PixFmt('yuv420p'))
        o1.add_option(Height(800))

        o2.add_option(Height(800))
        o2.add_option(PixFmt('yuv420p'))

        self.assertEqual(o1, o2)

        # Same test with twice the same option
        o1 = Options()
        o2 = Options()
        o1.add_option(Height(1500))
        o1.add_option(PixFmt('yuv420p'))
        o1.add_option(Height(800))

        o2.add_option(Height(800))
        o2.add_option(PixFmt('yuv420p'))
        o2.add_option(Height(1500))

        self.assertEqual(o1, o2)

    def test_subset(self):
        pass


class TestContainers(unittest.TestCase):
    def setUp(self):
        from mediaprocessor.converter.parsers import FFprobeParser
        from mediaprocessor.converter.streams import VideoStream, AudioStream, SubtitleStream
        with open('output.json', 'r') as infile:
            input = infile.read()
        self.parser = FFprobeParser(input)
        self.video_stream = VideoStream(FormatFactory.get_format('h264'))
        self.video_stream.add_options(PixFmt('yuv420p'),
                                      Height(800),
                                      Disposition({'default': 1}),
                                      Width(1920),
                                      Level(4.0),
                                      Profile('High'),
                                      Bitrate(2052)
                                      )


    def test_source_container(self):
        from mediaprocessor.converter.containers import ContainerFactory
        source_container = ContainerFactory.container_from_parser(self.parser)
        self.assertEqual(source_container.format, 'matroska')
        self.assertEqual(source_container.streams[0], self.video_stream)
