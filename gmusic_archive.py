#!/usr/bin/env python3

"""\
Download all of my music from Google Play Music.
"""

# TODO: generate metadata

import os
import re
import time

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
@click.option('-D', '--db-name', default='gmusic-archive.db',
              help='The database to use for queuing the songs.')
@click.option('--debug/--no-debug', default=False,
              help='Print extra debugging information.')
@click.pass_context
def cli(ctx, db_name, debug):
    ctx.obj = {}

    ctx.obj['DB_NAME'] = db_name
    ctx.obj['DEBUG'] = debug

    db_uri = 'sqlite:///' + db_name
    create = not os.path.exists(db_name)
    engine = create_engine(db_uri, echo=debug)
    Session.configure(bind=engine)
    if create:
        Base.metadata.create_all(engine)

    ctx.obj['DB_URI'] = db_uri


@cli.command()
@click.pass_context
def authorize(ctx):
    """Authorize this client to access your music library."""
    debug = ctx.obj['DEBUG']
    music = Musicmanager(debug_logging=debug)
    music.perform_oauth(open_browser=True)


@cli.command()
@click.option('-c', '--clear/--no-clear',
              help='Clear the database before populating it.')
@click.pass_context
def get_songs(ctx, clear):
    """Download the list of songs to download."""
    debug = ctx.obj['DEBUG']

    music = Musicmanager(debug_logging=debug)
    music.login()

    downloaded = music.get_uploaded_songs()
    purchased = music.get_purchased_songs()

    print('You have:')
    print('\t{} uploaded songs'.format(len(downloaded)))
    print('\t{} purchased songs'.format(len(purchased)))

    session = Session()
    if clear:
        session.query(Song).delete()

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
def info():
    """Show information about the song counts."""
    session = Session()

    total = session.query(Song).count()
    in_process = session.query(Song).filter(Song.file_location == '*').count()
    to_download = session.query(Song).filter(Song.file_location == None).count()
    print('{:6} total songs.'.format(total))
    print('{:6} in process.'.format(in_process))
    print('{:6} to download.'.format(to_download))


@cli.command()
@click.option('-o', '--output-dir', default='./archive',
              type=click.Path(file_okay=False, dir_okay=True),
              help='The directory to put the songs into.')
@click.pass_context
def archive(ctx, output_dir):
    """Download songs."""
    debug = ctx.obj['DEBUG']
    music = Musicmanager(debug_logging=debug)
    music.login()

    session = Session()

    count = 0
    while True:
        if count:
            time.sleep(60)

        current = session.query(Song).filter(
            Song.file_location == None
            ).first()
        save_filename(session, current, '*')

        count += 1
        print('{:4}. {} / {}'.format(count, current.artist, current.title), end='')
        try:
            (filename, song_data) = music.download_song(current.play_id)
            parts = [
                normalize_path(current.album_artist or current.artist),
                normalize_path(current.album),
                normalize_path(current.title),
                ]
            parts = [part for part in parts if part is not None]

            output = os.path.join(output_dir, *parts)
            os.makedirs(output)

            output = os.path.join(output, filename)

            print(' => {}'.format(output))

            with open(output, 'wb') as fout:
                fout.write(song_data)

        except:
            save_filename(session, current, None)
            raise

        save_filename(session, current, output)


@cli.command()
# @click.pass_context
def save_metadata():
    """Save the metadata in a YAML file beside every song."""
    raise NotImplemented()


def normalize_path(inp):
    """Normalizes a path component by lowercasing and changing all
    non-alphanumeric characters to dashes."""
    return re.sub(r'\W+', '-', inp.lower()) if inp is not None else None


def save_filename(session, song, filename):
    """Saves the file location."""
    song.file_location = filename
    session.add(song)
    session.commit()


if __name__ == '__main__':
    cli()
