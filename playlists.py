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
    music = Mobileclient(debug_logging=DEBUG)
    # gmusicapi.Mobileclient.perform_oauth('mobileclient.cred')
    music.oauth_login(Mobileclient.FROM_MAC_ADDRESS, 'mobileclient.cred')

    playlists = music.get_all_user_playlist_contents()
    json.dump(playlists, sys.stdout)


if __name__ == '__main__':
    main()

