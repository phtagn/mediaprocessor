from mediaprocessor.configuration_mod import configuration
import logging
from transitions import Machine, State
from mediaprocessor.processor import processor
from mediaprocessor.fetchers.fetchers import FetchersFactory, FetcherException
from mediaprocessor.taggers import tagger
from mediaprocessor.helpers.helpers import breakdown
from mediaprocessor.refreshers.refreshers import RefresherFactory
import shutil
import os

import sys

log = logging.getLogger()
log.setLevel(logging.DEBUG)
sh = logging.StreamHandler(sys.stdout)
sh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s - %(message)s')
sh.setFormatter(formatter)
log.addHandler(sh)


# log = logging.getLogger(__name__)


class VideoProcessor(object):

    def __init__(self, infile: str, target: str, config: str = None, overrides: dict = None, tagging_info: dict = None,
                 notify: list = None):
        """
        Videoprocessor contains the methods to process a video from start to finish. The steps are :
        1) Analyse the input file to determine the source source_container, and create the theoretical target source_container
        2) Convert the input file into the output file
        3) Tag the output file
        4) Postprocess, e.g. for mp4 do qtfaststart
        5) Deploy the output file to its destination
        6) Notify various apps of the
        :param infile: path to the input file
        :param target: extension of source_container, e.g. mp4, mkv
        :param config: name of the configuration file, relative to the config directory
        :param overrides: a dictionary containing overrides to the configuration file
        :param tagging_info: a dictionary in the same form as the config file. Does not need to contain all
        the configuration file entries, just those you want to override
        :param notify: a dictionary holding the list of applications to notify
        """
        conf = configuration.CfgMgr()

        if config:
            try:
                conf.load(config, overrides=overrides)
                self.config = conf.cfg
            except FileNotFoundError:
                raise Exception('Config %s is not available in config directory', config)
        else:
            self.config = conf.defaultconfig

        if target in self.config['Containers'].keys():
            self.target = target
        else:
            raise Exception(f'Unsupported source_container, valid containers are {self.config.keys()}')

        self.copy_folder = None
        self.move_folder = None
        self.output_container = None

        path = os.path.abspath(infile)
        if os.path.isfile(path):
            self.inputfile = path
        else:
            raise FileNotFoundError(f'File {path} does not exist')

        if self.config['File'].get('work_directory') and os.path.isdir(self.config['File'].get('work_directory')):
            self.work_dir = os.path.abspath(self.config['File'].get('work_directory'))
        else:
            self.work_dir = os.path.abspath(breakdown(self.inputfile)['dir'])

        if self.config['File'].get('copy_to') and os.path.isdir(self.config['File'].get('copy_to')):
            self.copy_folder = os.path.abspath(self.config['File'].get('copy_to'))

        if self.config['File'].get('move_to') and os.path.isdir(
                self.config['File'].get('move_to')) and not self.copy_folder:
            self.move_folder = os.path.abspath(self.config['File'].get('move_to'))

        self.delete_original = self.config['File'].get('delete_original')

        self.tagging_info = tagging_info
        self.tv_fetcher = self.config['Tagging'].get('preferred_show_tagger', 'tvdb')
        self.movie_fetcher = self.config['Tagging'].get('preferred_movie_tagger', 'tmdb')
        self.download_artwork = self.config['Tagging'].get('download_artwork')

        work_file = os.path.join(self.work_dir, breakdown(self.inputfile)['file'] + '-working.' + self.target)

        self.processor = processor.Processor(self.config, self.inputfile, work_file, self.target)
        self.refreshers = []

        if notify:
            for r in notify:
                if r in self.config['Refreshers']:
                    refresher = RefresherFactory.get_refesher(r, **self.config['Refreshers'][r])
                    if refresher:
                        self.refreshers.append(refresher)

    def conversion_success(self):
        if self.output_container and os.path.exists(self.output_container.file_path):
            return True
        return False

    def has_tag_info(self):
        if self.tagging_info:
            return True
        return False

    def has_copy_info(self):
        if self.copy_folder:
            return True
        return False

    def has_move_info(self):
        if self.move_folder:
            return True
        return False

    def has_delete(self):
        return self.delete_original

    def has_refresher(self):
        if self.refreshers:
            return True
        return False

    def do_process(self):
        """
        Processes the sourcefile into a target source_container
        :return: None
        """
        self.output_container = self.processor.process()  # type: converter.containers.Container

    def do_tag(self):
        _id = self.tagging_info.get('id', None)
        id_type = self.tagging_info.get('id_type', None)
        season = self.tagging_info.get('season', None)
        episode = self.tagging_info.get('episode', None)
        language = self.config['Languages'].get('tagging')

        fetcher = self.tv_fetcher if season else self.movie_fetcher

        try:
            ftch = FetchersFactory.getfetcher(fetcher, _id, id_type, language=language, season=season, episode=episode)
            tags = ftch.gettags()
        except FetcherException:
            return None

        if tags.poster_url and self.download_artwork:
            poster_file = ftch.downloadArtwork(tags.poster_url)
        else:
            poster_file = None

        t = tagger.TaggerFactory.get_tagger(self.target, tags, self.output_container.file_path,
                                            artwork_file=poster_file, is_hd=self.output_container.hd)
        if t:
            t.writetags()
        else:
            log.info('Tagging is not supported for source_container %s at this time, skipping',
                     self.target)

    def do_postprocess(self):
        from mediaprocessor.postprocesses import PostProcessorFactory
        try:
            postprocesses = PostProcessorFactory.get_post_processors(
                self.config['Containers'][self.target].get('post_processors'))
        except:
            log.info('No post processing needed')
            postprocesses = None

        if postprocesses:
            for postprocess in postprocesses:
                postprocess().process(self.output_container.file_path)

    def do_deploy(self):
        path_elements = breakdown(self.inputfile)
        try:
            os.rename(self.output_container.file_path, os.path.join(self.work_dir,
                                                                    path_elements['file'] + '.' + self.target))
            infile = os.path.join(self.work_dir, path_elements['file'] + '.' + self.target)
        except FileNotFoundError:
            raise FileNotFoundError

        if self.copy_folder:
            if os.access(self.copy_folder, os.W_OK):
                try:
                    shutil.copy2(infile,
                                 os.path.join(self.copy_folder, path_elements['file'] + '.' + self.target))
                except:
                    raise Exception('Error while copying file')
            else:
                log.error('Directory %s is not writeable', self.copy_folder)

            log.info('%s copied to folder(s)  %s', self.output_container,
                     os.path.join(self.copy_folder, path_elements['file'] + '.' + self.target))

        elif self.move_folder:
            if os.access(self.move_folder, os.W_OK):
                try:
                    os.rename(infile, os.path.join(self.move_folder, path_elements['file'] + '.' + self.target))
                except:
                    log.exception('Error while moving file')
            else:
                log.error('Directory %s is not writeable', self.move_folder)

    def do_delete(self):
        try:
            os.chmod(self.inputfile, int("0777", 8))
        except:
            log.debug('File maybe read only')

        if os.path.exists(self.inputfile):
            try:
                os.remove(self.inputfile)
            except:
                log.exception('Original file %s could not be deleted', self.inputfile)
                return False

    def do_refresh(self):
        for r in self.refreshers:
            r.refresh('movie')


def build_machine(infile, target, config, tagging_info=None, notify=None):
    videoprocessor = VideoProcessor(infile, target, config, tagging_info=tagging_info, notify=notify)
    machine = Machine(model=videoprocessor, initial='initialised')

    states = ['initialised',
              State(name='processed'),
              State(name='tagged'),
              State(name='postprocessed'),
              State(name='refreshed'),
              State(name='deployed'),
              State(name='deleted'),
              State(name='finished')
              ]

    machine.add_states(states)

    machine.add_transition(trigger='process', source='initialised', dest='processed',
                           before='do_process')

    machine.add_transition(trigger='tag', source='processed', dest='tagged',
                           conditions=['conversion_success', 'has_tag_info'],
                           before='do_tag')

    machine.add_transition(trigger='postprocess', source=['tagged', 'processed'], dest='postprocessed',
                           conditions=['conversion_success'],
                           before='do_postprocess')

    machine.add_transition(trigger='deploy', source=['processed', 'tagged', 'postprocessed'], dest='deployed',
                           conditions='conversion_success', before='do_deploy')

    machine.add_transition(trigger='delete', source=['postprocessed', 'deployed'],
                           dest='deleted',
                           conditions=['has_delete'],
                           before='do_delete')

    machine.add_transition(trigger='refresh',
                           source=['processed', 'tagged', 'deployed', 'deleted'],
                           conditions=['has_refresher'], dest='refreshed',
                           before='do_refresh')

    machine.add_transition(trigger='finish',
                           source=['processed', 'tagged', 'postprocessed', 'refreshed', 'deployed', 'deleted'],
                           dest='finished')

    return videoprocessor


def start_machine(infile, target, config, tagging_info=None, notify=None):
    vp = build_machine(infile, target, config, tagging_info=tagging_info, notify=notify)
    vp.process()
    vp.tag()
    vp.postprocess()
    vp.deploy()
    vp.delete()
    vp.refresh()
    vp.finish()


if __name__ == '__main__':
    showid = 75978
    id_type2 = 'tvdb_id'
    #tagging_info = {'id': 75978, 'id_type': 'tvdb_id', 'season': 16, 'episode': 19}
    laptop = os.path.abspath('/Users/Jon/Downloads/in/The.Polar.Express.(2004).1080p.BluRay.MULTI.x264-DiG8ALL.mkv')
    desktop = os.path.abspath("/Users/Jon/Downloads/geo.mkv")
    blade = os.path.abspath(
        '/Users/jon/Downloads/Blade.Runner.2049.2017.VF2.2160p.UHD.BluRay.REMUX.HEVC.HDR.TrueHD.Atmos.7.1.DTS-HDMA.AC3.5.1-TSC.mkv')
    configname = 'defaults.ini'
    tgt = 'mp4'
    info = {'id': showid,
            'id_type': id_type2,
            'season': 16,
            'episode': 18
            }

    VP = build_machine(infile=desktop, config=configname, target=tgt, tagging_info=None, notify=None)

    start_machine(VP)
    print('yeah')
