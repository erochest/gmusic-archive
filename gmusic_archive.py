#!/usr/bin/env python3

"""\
Download all of my music from Google Play Music.
"""

import datetime
import json
import math
import os
from pathlib import Path, PurePath
import random
import re
import time

import click
from gmusicapi import Mobileclient, Musicmanager
from sqlalchemy import (create_engine, Column, ForeignKey, Integer, String, Table)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker


Base = declarative_base()
Session = sessionmaker()


playlist_song_table = Table(
        'playlist_song',
        Base.metadata,
        Column('song_id', Integer, ForeignKey('songs.id')),
        Column('playlist_id', Integer, ForeignKey('playlists.id')),
        )


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


class Playlist(Base):
    __tablename__ = 'playlists'

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False)
    google_id = Column(String, nullable=False)

    songs = relationship(
            'Song',
            secondary=playlist_song_table,
            )


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
    ctx.obj['DB_URI'] = open_db(db_name)


def open_db(db_name, debug=False):
    """Opens the database and returns the URI."""
    db_uri = 'sqlite:///' + db_name
    engine = create_engine(db_uri, echo=debug)
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)
    return db_uri


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
@click.option('--delay', default=60, type=int,
              help='The delay between downloads in seconds. '
                   'Default is 60.')
@click.pass_context
def archive(ctx, output_dir, delay):
    """Download songs."""
    debug = ctx.obj['DEBUG']
    delay_range = math.floor(delay * 0.1)
    music = Musicmanager(debug_logging=debug)
    music.login()

    session = Session()

    count = 0
    while True:
        if count:
            time.sleep(delay + (random.randrange(-delay_range, delay_range)))

        current = session.query(Song).filter(
            Song.file_location == None
            ).first()
        if current is None:
            break
        save_filename(session, current, '*')

        count += 1
        now = datetime.datetime.now()
        print('[{}] {} / {}'.format(
            now.isoformat(),
            current.artist,
            current.title
            ), end='')
        try:
            (filename, song_data) = music.download_song(current.play_id)
            parts = [
                normalize_path(current.album_artist or current.artist),
                normalize_path(current.album),
                normalize_path(current.title),
                ]
            parts = [part[:20] for part in parts if part is not None]

            output = os.path.join(output_dir, *parts)
            os.makedirs(output, exist_ok=True)

            output = os.path.join(output, filename)

            print(' => {}'.format(output))

            with open(output, 'wb') as fout:
                fout.write(song_data)

        except:
            save_filename(session, current, None)
            raise

        save_filename(session, current, output)


@cli.command()
@click.option('-l', '--login', is_flag=True, default=False, help='If you need to login, set this flag.')
@click.pass_context
def playlists(ctx, login):
    """Download playlists."""
    debug = ctx.obj['DEBUG']

    music = Mobileclient(debug_logging=debug)
    if login:
        music.perform_oauth()
        return
    else:
        music.oauth_login(device_id=Mobileclient.FROM_MAC_ADDRESS)
    playlists = music.get_all_user_playlist_contents()

    session = Session()
    song_index = {song.play_id: song for song in session.query(Song).all()}

    for playlist in playlists:
        tracks = playlist.get('tracks')
        if not tracks:
            if debug:
                print('skipping playlist "{}"'.format(playlist['name'])) 
            continue

        db_playlist = Playlist(
                name=playlist['name'],
                google_id=playlist['id'],
                )
        db_playlist.songs = [
                song_index[t['trackId']]
                for t in tracks
                if t['trackId'] in song_index
                ]

        session.add(db_playlist)

    session.commit()


@cli.command()
@click.option('-o', '--output', type=click.File('w'),
              help='Write the database as metadata.')
def save_metadata(output):
    """Save the metadata into a JSON file."""
    session = Session()
    songs = []
    for song in session.query(Song).all():
        song = song.__dict__
        song.pop('_sa_instance_state', None)
        songs.append(song)
    json.dump(songs, output, indent=4)


@cli.command()
@click.pass_context
def collapse_tree(ctx):
    """This hoists songs up out of their immediate parent directory.

    For example, it changes `a/b/c` into `a/c`.

    Originally, the archived each song into its own directory. This grops
    them better.
    """
    debug = ctx.obj['DEBUG']
    session = Session()
    count = 0
    for song in session.query(Song).all():
        src = Path(song.file_location)

        src_parts = list(src.parts)
        del src_parts[-2]
        dest = Path(*src_parts)

        if debug:
            print('mv {} => {}'.format(src, dest))

        if src.exists() and not dest.exists():
            src.rename(dest)
        if src.parent.exists() and not list(src.parent.iterdir()):
            src.parent.rmdir()

        song.file_location = str(dest)
        session.add(song)

        count += 1

    if debug:
        print('{} files moved'.format(count))
    session.commit()


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
