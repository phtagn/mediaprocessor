from setuptools import setup

setup(
    name='mediaprocessor',
    version='1.0',
    packages=['mediaprocessor'],
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
