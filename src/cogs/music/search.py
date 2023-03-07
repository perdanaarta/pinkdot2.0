from abc import ABC
from dataclasses import dataclass
import wavelink
from wavelink.ext import spotify
from .utils import Track, YouTubeTrackList, SpotifyTrackList

from utils.logger import logger
import config

from async_spotify import SpotifyApiClient
from async_spotify.authentification.authorization_flows import ClientCredentialsFlow
from async_spotify.spotify_errors import SpotifyAPIError


class YouTubeSearch(ABC):
    @staticmethod
    def get_track(wavelink: wavelink.Track):
        return Track(
            title=wavelink.title,
            url=wavelink.uri,
            thumbnail=wavelink.thumbnail,
            wavelink=wavelink
        )

    @classmethod
    async def search(cls, query: str, amount: int=5) -> list[Track]:
        wave_list = []
        for wave in (await wavelink.YouTubeMusicTrack.search(query))[:amount]:
            wave_list.append(
                cls.get_track(wave)
            )
        return wave_list
    
    @classmethod
    async def video(cls, url: str) -> Track:
        wave = await wavelink.YouTubeTrack.search(query=url, return_first=True)
        return cls.get_track(wave)
    
    async def playlist(url: str) -> YouTubeTrackList:
        wave: wavelink.YouTubePlaylist = await wavelink.YouTubePlaylist.search(url)

        return YouTubeTrackList(
            name = wave.name,
            url = url,
            thumbnail= wave.tracks[0].thumbnail,
            tracks = wave.tracks
        )


class SpotifySearch(ABC):
    spotify_client = None

    @classmethod
    async def init(cls) -> None:
        cls.spotify_client = SpotifyApiClient(authorization_flow=ClientCredentialsFlow(
            application_id=config.SPOTIFY_CLIENT_ID,
            application_secret=config.SPOTIFY_CLIENT_SECRET
        ))
        await cls.spotify_client.get_auth_token_with_client_credentials()
        await cls.spotify_client.create_new_client()
        logger.info("Logged into spotify")

    @classmethod
    async def close(cls) -> None:
        await cls.spotify_client.close_client()
        cls.spotify_client = None

    @staticmethod
    def get_spotify_id(url: str):
        return list(filter(None, url.split('/')))[-1].split('?')[0]

    @staticmethod
    def get_track(wavelink: wavelink.Track):
        return Track(
            title=wavelink.title,
            url=wavelink.uri,
            thumbnail=wavelink.thumbnail,
            wavelink=wavelink
        )
        
    @classmethod
    async def track(cls, query):
        track = await spotify.SpotifyTrack.search(
            query=query,
            type=spotify.SpotifySearchType.track,
            return_first=True
        )
        return cls.get_track(track)

    @classmethod
    async def album(cls, url):
        album_id = cls.get_spotify_id(url)
        try:
            album = await cls.spotify_client.albums.get_one(album_id)
        except SpotifyAPIError:
            return None
        
        try:
            album_thumbnail = album['images'][0]['url']
        except:
            album_thumbnail = 'https://i.ytimg.com/vi_webp/_/maxresdefault.webp'

        return SpotifyTrackList(
            name=album["name"],
            url=url,
            thumbnail=album_thumbnail,
            type="album"
        )
            
    @classmethod
    async def playlist(cls, url):
        playlist_id = cls.get_spotify_id(url)
        try:
            playlist = await cls.spotify_client.playlists.get_one(playlist_id)
        except SpotifyAPIError:
            return None
        
        try:
            playlist_thumbnail = playlist['images'][0]['url']
        except:
            playlist_thumbnail = 'https://i.ytimg.com/vi_webp/_/maxresdefault.webp'

        return SpotifyTrackList(
            name=playlist["name"],
            url=url,
            thumbnail=playlist_thumbnail,
            type="playlist"
        )