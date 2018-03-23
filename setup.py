from setuptools import setup

setup(
    name="gmusic-archive",
    version="0.1",
    py_modules=["gmusic_archive"],
    install_requires=[
        'click',
        'gmusicapi',
        ],
    entry_points='''
        [console_scripts]
        gmusic_archive=gmusic_archive:cli
        ''',
    )
