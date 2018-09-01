import json
import locale
import os
from mediaprocessor.converter.options import *
from mediaprocessor.converter.formats import FormatFactory

log = logging.getLogger(__name__)

console_encoding = locale.getdefaultlocale()[1] or 'UTF-8'


class FFprobeParser(object):

    def __init__(self, jsonoutput):
        output = json.loads(jsonoutput)
        self._streams = output['streams']
        self._format = output['format']

    @property
    def streams(self):
        return self._streams

    @property
    def container_format(self):
        return self._format['format_name'].lower()

    @property
    def file_path(self):
        return os.path.abspath(self._format['filename'])

    def pix_fmt(self, index) -> PixFmt:
        return PixFmt(self.streams[index].get('pix_fmt', ''))

    def bitrate(self, index) -> Bitrate:
        if self.streams[index].get('bit_rate', 0):
            br = int(self.streams[index]['bit_rate'])
        else:
            try:
                br = int(self.streams[index]['tags'].get('BPS', 0))
            except KeyError:
                return Bitrate(0)

        return Bitrate(int(br / 1000))

    def stream_format(self, index):
        fmt = FormatFactory.get_format(self.streams[index].get('codec_name', ''))
        if not fmt:
            raise Exception(f'{self.streams[index].get("codec_name", "")}, unknown')
        # return Codec(self.streams[index].get('codec_name', ''))
        return fmt

    def channels(self, index) -> Channels:
        return Channels(self.streams[index].get('channels', 0))

    def height(self, index) -> Height:
        return Height(self.streams[index].get('height', 0))

    def width(self, index) -> Width:
        return Width(self.streams[index].get('width', 0))

    def language(self, index):
        try:
            return Language(self.streams[index]['tags'].get('language', 'und'))
        except KeyError:
            return Language('und')

    def disposition(self, index) -> Disposition:
        return Disposition(self.streams[index].get('disposition', {}))

    def level(self, index) -> Level:
        return Level(float(self.streams[index].get('level', 0.0)) / 10)

    def profile(self, index) -> Profile:
        return Profile(self.streams[index].get('profile', ''))

    def codec_type(self, index: Union[int, str]) -> Union[str, None]:
        return self.streams[index].get('codec_type', None)
