#!/usr/bin/env python3

"""\
Download playlists.
"""


import json
import os
import sys

from gmusicapi import Mobileclient


DEBUG = True


def main():
    """Download the playlist and save as JSON."""
    login_info = os.environ.get('GOOGLE_MUSIC_LOGIN')
    email, password = login_info.split(':')

    music = Mobileclient(debug_logging=DEBUG)
    music.login(email, password, Mobileclient.FROM_MAC_ADDRESS)

    playlists = music.get_all_user_playlist_contents()
    json.dump(playlists, sys.stdout)


if __name__ == '__main__':
    main()

