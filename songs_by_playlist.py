#!/usr/bin/env python3


"""Joins playlists and songs JSON files."""


import csv
import json
import sys


def track_set(tracks):
    """Return a set of track IDs."""
    return set(track['trackId'] for track in tracks)


def iter_songs(playlist_index, song_index):
    """Iterate over songs in every playlist."""
    for playlist_name, tracks in playlist_index.items():
        for track_id in tracks:
            song = song_index[track_id]
            yield (
                song['title'],
                song['album'][:20],
                song['artist'][:20],
                playlist_name,
                )


def main():
    """\
    Join the playlists and songs JSON files and output main information.
    """
    with open('playlists.json') as fin:
        playlists = json.load(fin)
    with open('songs.json') as fin:
        songs = json.load(fin)

    song_index = {song['play_id']: song for song in songs}
    playlist_index = {
        playlist['name']: track_set(playlist['tracks'])
        for playlist in playlists
        if playlist['tracks']
        }

    writer = csv.writer(sys.stdout, dialect='excel-tab')
    writer.writerows(iter_songs(playlist_index, song_index))


if __name__ == '__main__':
    main()
