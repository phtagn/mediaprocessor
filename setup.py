from setuptools import setup

setup(
    name='mediaprocessor',
    version='1.0',
    packages=['mediaprocessor',
              'mediaprocessor.config',
              'mediaprocessor.converter',
              'mediaprocessor.fetchers',
              'mediaprocessor.helpers',
              'mediaprocessor.refreshers',
              'mediaprocessor.taggers',
              ],
    url='',
    license='GPL',
    author='Jon',
    author_email='phtagn@gmail.com',
    description='Processes media files',
    install_requires=[
        'babelfish',
        'qtfaststart',
        'transitions',
        'tmdbsimple',
        'mutagen',
        'configobj',
        'tvdb-api',
        'requests'
        ]
)
