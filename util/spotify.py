from base64 import b64encode

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

import requests
import json
import os
import random

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_SECRET_ID = os.getenv("SPOTIFY_SECRET_ID")
BASE_URL = os.getenv("BASE_URL")

REDIRECT_URI = "{}/callback".format(BASE_URL)

# scope user-read-currently-playing,user-read-recently-played
SPOTIFY_URL_REFRESH_TOKEN = "https://accounts.spotify.com/api/token"
SPOTIFY_URL_NOW_PLAYING = "https://api.spotify.com/v1/me/player/currently-playing?additional_types=track,episode"
SPOTIFY_URL_RECENTLY_PLAY = "https://api.spotify.com/v1/me/player/recently-played"

SPOTIFY_URL_GENERATE_TOKEN = "https://accounts.spotify.com/api/token"
SPOTIFY_URL_USER_INFO = "https://api.spotify.com/v1/me"

class InvalidTokenError(Exception):
    pass


class RateLimitError(Exception):
    pass

def get_authorization():

    return b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_SECRET_ID}".encode()).decode(
        "ascii"
    )

def generate_token(authorization_code):

    data = {
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code": authorization_code,
    }

    headers = {"Authorization": f"Basic {get_authorization()}"}

    response = requests.post(SPOTIFY_URL_GENERATE_TOKEN, data=data, headers=headers)
    response_json = response.json()

    return response_json

def refresh_token(refresh_token):

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    headers = {"Authorization": f"Basic {get_authorization()}"}

    response = requests.post(SPOTIFY_URL_REFRESH_TOKEN, data=data, headers=headers)
    response_json = response.json()

    return response_json

def get_user_profile(access_token):

    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(SPOTIFY_URL_USER_INFO, headers=headers)
    response_json = response.json()

    return response_json

def get_recently_play(access_token, limit=10):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        SPOTIFY_URL_RECENTLY_PLAY, headers=headers, params={"limit": limit}
    )
    if response.status_code == 204:
        return {}
    if response.status_code == 401:
        raise InvalidTokenError("invalid or expired token")
    if response.status_code == 429:
        raise RateLimitError("rate limited")
    response.raise_for_status()
    response_json = response.json()
    return response_json

def get_now_playing(access_token):

    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(SPOTIFY_URL_NOW_PLAYING, headers=headers)

    if response.status_code == 204:
        return {}

    response_json = response.json()
    return response_json
