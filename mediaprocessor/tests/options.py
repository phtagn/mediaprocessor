import unittest
from mediaprocessor.converter.options import *


class TestOptionFactory(unittest.TestCase):
    def test_get_option(self):
        self.assertIsNone(OptionFactory.get_option('NonExistent'))
        self.assertIs(OptionFactory.get_option('codec'), Codec)

    def test_streamvalueoptions(self):
        opt1 = Bitrate(1000)
        opt2 = Bitrate(1001)
        self.assertGreater(opt2, opt1)

    def test_options(self):
        options = Options()
        options.add_option(Codec, True)


if __name__ == '__main__':
    unittest.main()
