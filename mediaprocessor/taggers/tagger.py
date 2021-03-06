import os
from io import BytesIO
from mutagen.mp4 import MP4, MP4Cover
import abc
import logging

log = logging.getLogger(__name__)


class TagError(Exception):
    pass


class ITagger(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def write(self):
        pass


class TaggerFactory(object):
    Taggers = {}

    @classmethod
    def register(cls, tagger):
        cls.Taggers.update({tagger.name: tagger})

    @classmethod
    def get_tagger(cls, tagger: str, tags, filepath: str, artwork_file=None, is_hd=False):
        if tagger in TaggerFactory.Taggers:
            return cls.Taggers[tagger](tags, filepath, artwork_file=artwork_file, is_hd=is_hd)
        else:
            return None


class MP4Tagger(ITagger):
    supported_containers = ['mp4']
    name = 'mp4'

    tag_table = {
        'description': 'desc',
        'long_description': 'ldes',
        'genre': '\xa9gen',
        'title': '\xa9nam',
        'show': 'tvsh',
        'episode_title': 'tven',
        'network': 'tvnn',
        'season_number': 'tvsn',
        'season_total': 'disk',
        'episode_number': 'tves',
        'track_number': 'trkn',
        'album': '\xa9alb',
        'itunes_video_category': 'stik',
        'resolution': 'hdvd'}

    def __init__(self, tags, mp4_path, artwork_file=None, is_hd=False):
        self.mp4_path = mp4_path
        self.tags = tags
        self.artwork_file = artwork_file
        self.is_hd = is_hd

        if os.path.isfile(mp4_path):
            self.video = MP4(self.mp4_path)
        else:
            log.error('Path %s is not valid', mp4_path)

        ext = os.path.splitext(self.mp4_path)[1][1:]
        if ext.lower() not in ['mp4', 'm4v', 'mov']:
            raise TaggerException('MP4Tagger only tags mp4, the file extention is %s', ext)

    def writetags(self):

        self.settag('description', self.tags.description)
        self.settag('long_description', self.tags.long_description)
        self.settag('genre', self.tags.genre)
        self.settag('title', self.tags.title)
        self.settag('date', self.tags.date)
        self.settag('show', self.tags.show)
        self.settag('episode_title', self.tags.title)
        self.settag('network', self.tags.network)
        self.settag('season_total', [(self.tags.season_total, 0)])
        self.settag('album', f'{self.tags.show}, Season {self.tags.season_total}')
        self.settag('episode_number', [self.tags.episode_number])
        self.settag('track_number', [(self.tags.episode_number, self.tags.season_total)])
        self.settag('resolution', self.setHD(self.is_hd))

        if self.tags.season_number:
            self.settag('itunes_video_category', [10])
        else:
            self.settag('itunes_video_category', [9])

        self.video["----:com.apple.iTunes:iTunMOVI"] = self.xmlTags()  # XML - see xmlTags method
        # self.video["----:com.apple.iTunes:iTunEXTC"] = self.setRating()  # iTunes content rating

        if self.artwork_file:
            cover = open(self.artwork_file, 'rb').read()
            if self.artwork_file.endswith('png'):
                self.video["covr"] = [MP4Cover(cover, MP4Cover.FORMAT_PNG)]  # png poster
            else:
                self.video["covr"] = [MP4Cover(cover, MP4Cover.FORMAT_JPEG)]  # jpeg poster

        MP4(self.mp4_path).delete(self.mp4_path)
        self.video.save()

    def settag(self, tag, tagdata=None) -> None:

        if tag in MP4Tagger.tag_table and tagdata:
            mp4tag = MP4Tagger.tag_table[tag]
            self.video[mp4tag] = tagdata
        else:
            log.debug('Tag %s was not written because data %s was missing', tag, tagdata)

    @staticmethod
    def setHD(is_hd):
        if is_hd == '720p':
            return ['1']
        elif is_hd == '1080p':
            return ['2']

        return ['0']

    def xmlTags(self):
        # constants
        header = b"<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\"><plist version=\"1.0\"><dict>\n"
        castheader = b"<key>cast</key><array>\n"
        writerheader = b"<key>screenwriters</key><array>\n"
        directorheader = b"<key>directors</key><array>\n"
        subfooter = b"</array>\n"
        footer = b"</dict></plist>\n"

        output = BytesIO()
        output.write(header)

        # Write actors
        if self.tags.cast:
            output.write(castheader)
            for name in self.tags.cast:
                tag = name if name.__class__ is bytes else name.encode('ascii', errors='ignore')
                output.write(b"<dict><key>name</key><string>%s</string></dict>\n" % tag)
                output.write(subfooter)

        # Write screenwriterr
        if self.tags.writers:
            output.write(writerheader)
            for name in self.tags.writers:
                tag = name if name.__class__ is bytes else name.encode('ascii', errors='ignore')
                output.write(
                    b"<dict><key>name</key><string>%s</string></dict>\n" % tag)
            output.write(subfooter)

        # Write directors
        if self.tags.directors:
            output.write(directorheader)
            for name in self.tags.directors:
                tag = name if name.__class__ is bytes else name.encode('ascii', errors='ignore')
                output.write(
                    b"<dict><key>name</key><string>%s</string></dict>\n" % tag)
            output.write(subfooter)

        # Close XML

        output.write(footer)
        return output.getvalue()


TaggerFactory.register(MP4Tagger)


class TaggerException(Exception):
    pass
