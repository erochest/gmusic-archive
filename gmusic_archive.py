#!/usr/bin/env python3

"""\
Download all of my music from Google Play Music.
"""


import os

import click
from gmusicapi import Musicmanager
from sqlalchemy import (create_engine, Column, Integer, String)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


Base = declarative_base()
Session = sessionmaker()


class Song(Base):
    __tablename__ = 'songs'

    id = Column(Integer, primary_key=True)

    play_id = Column(String, nullable=False)
    title = Column(String)
    album = Column(String)
    album_artist = Column(String)
    artist = Column(String)
    track_number = Column(String)
    track_size = Column(String)
    disc_number = Column(String)
    total_disc_count = Column(String)

    file_location = Column(String, nullable=True)


@click.group()
def cli():
    pass


@cli.command()
@click.option('-d', '--debug', is_flag=True,
              help='Print extra debugging information.')
def authorize(debug):
    """Authorize this client to access your music library."""
    music = Musicmanager(debug_logging=debug)
    music.perform_oauth(open_browser=True)


@cli.command()
@click.option('-D', '--db-name', default='gmusic-archive.db',
              help='The database to use for queuing the songs.')
@click.option('-d', '--debug', is_flag=True,
              help='Print extra debugging information.')
def get_songs(db_name, debug):
    """Download the list of songs to download."""
    music = Musicmanager(debug_logging=debug)
    music.login()

    downloaded = music.get_uploaded_songs()
    purchased = music.get_purchased_songs()

    print('You have:')
    print('\t{} uploaded songs'.format(len(downloaded)))
    print('\t{} purchased songs'.format(len(purchased)))

    db_uri = 'sqlite:///' + db_name
    create = not os.path.exists(db_name)
    engine = create_engine(db_uri, echo=debug)
    Session.configure(bind=engine)
    if create:
        Base.metadata.create_all(engine)

    session = Session()
    for gmusic_song in downloaded:
        song = Song(
            play_id=gmusic_song['id'],
            title=gmusic_song['title'],
            album=gmusic_song['album'],
            album_artist=gmusic_song['album_artist'],
            artist=gmusic_song['artist'],
            track_number=gmusic_song['track_number'],
            track_size=gmusic_song['track_size'],
            disc_number=gmusic_song['disc_number'],
            total_disc_count=gmusic_song['total_disc_count'],
            )
        session.add(song)
    for gmusic_song in purchased:
        song = Song(
            play_id=gmusic_song['id'],
            title=gmusic_song['title'],
            album=gmusic_song['album'],
            album_artist=gmusic_song['album_artist'],
            artist=gmusic_song['artist'],
            track_number=gmusic_song['track_number'],
            track_size=gmusic_song['track_size'],
            disc_number=gmusic_song['disc_number'],
            total_disc_count=gmusic_song['total_disc_count'],
            )
        session.add(song)

    session.commit()

@cli.command()
@click.option('-D', '--db-name', default='gmusic-archive.db',
              help='The database to use for queuing the songs.')
@click.option('-d', '--debug', is_flag=True,
              help='Print extra debugging information.')
def info(db_name, debug):
    """Show information about the song counts."""
    db_uri = 'sqlite:///' + db_name
    create = not os.path.exists(db_name)
    engine = create_engine(db_uri, echo=debug)
    Session.configure(bind=engine)
    if create:
        Base.metadata.create_all(engine)

    session = Session()

    total = session.query(Song).count()
    to_download = session.query(Song).filter(Song.file_location == None).count()
    print('{:6} total songs.'.format(total))
    print('{:6} to download.'.format(to_download))



if __name__ == '__main__':
    cli()
