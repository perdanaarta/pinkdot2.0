from abc import ABC
from dataclasses import dataclass
import wavelink
from .utils import Track, TrackList

from utils.logger import logger
import config

from async_spotify import SpotifyApiClient
from async_spotify.authentification.authorization_flows import ClientCredentialsFlow
from async_spotify.spotify_errors import SpotifyAPIError


class YouTubeSearch(ABC):
    def get_track(wavelink: wavelink.Track):
        return Track(
            title=wavelink.title,
            url=wavelink.uri,
            thumbnail=wavelink.thumbnail,
            wavelink=wavelink
        )

    @classmethod
    async def search(cls, query: str, amount: int=5) -> list[Track]:
        wv_list = []
        for wv in (await wavelink.YouTubeMusicTrack.search(query))[:amount]:
            wv_list.append(
                cls.get_track(wv)
            )
        return wv_list
    
    @classmethod
    async def video(cls, url: str) -> Track:
        wv = await wavelink.YouTubeTrack.search(query=url, return_first=True)
        return cls.get_track(wv)
    
    async def playlist(url: str) -> TrackList:
        wv: wavelink.YouTubePlaylist = await wavelink.YouTubePlaylist.search(url)

        return TrackList(
            name = wv.name,
            url = url,
            thumbnail= wv.tracks[0].thumbnail,
            type = "youtube_playlist",
            tracks = wv.tracks
        )
    
class SpotifySearch(ABC):
    spotify_client: SpotifyApiClient | None = None

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
    async def get_wavelink(query: str):
        return await wavelink.YouTubeMusicTrack.search(query, return_first=True)
    
    @classmethod
    async def fetch_all_tracks(cls, info: dict) -> dict:
        next_link = info['tracks']['next']
        while next_link:
            next_tracks = await cls.spotify_client.next(next_link)
            info['tracks']['items'] += next_tracks['items']
            next_link = next_tracks['next']
        return info

    @classmethod
    async def track(cls, url: str) -> Track | None:
        track_id = cls.get_spotify_id(url)
        try:
            track = await cls.spotify_client.track.get_one(track_id)
        except SpotifyAPIError:
            return None

        track_name = track['artists'][0]['name']
        for i in range(len(track['artists']) - 1):
            track_name += ', ' + track['artists'][i + 1]['name']
        track_name += ' - ' + track['name']

        try:
            track_thumbnail = track['album']['images'][0]['url']
        except:
            track_thumbnail = 'https://i.ytimg.com/vi_webp/nonexist/maxresdefault.webp'

        wavelink = await cls.get_wavelink(track_name)

        return Track(
            title=track_name,
            url=url,
            thumbnail=track_thumbnail,
            wavelink=wavelink
        )

    @classmethod
    async def album(cls, url: str) -> TrackList | None:
        album_id = cls.get_spotify_id(url)
        try:
            album = await cls.spotify_client.albums.get_one(album_id)
        except SpotifyAPIError:
            return None
        album = await cls.fetch_all_tracks(album)

        track_urls = []
        for track in album['tracks']['items']:
            track_urls.append(track['external_urls']['spotify'])

        try:
            album_thumbnail = album['images'][0]['url']
        except:
            album_thumbnail = 'https://i.ytimg.com/vi_webp/nonexist/maxresdefault.webp'

        return TrackList(
            name=album["name"],
            url=url,
            thumbnail=album_thumbnail,
            type="spotify_playlist",
            tracks=track_urls
        )

    @classmethod
    async def playlist(cls, url: str) -> TrackList | None:
        playlist_id = cls.get_spotify_id(url)
        try:
            playlist = await cls.spotify_client.playlists.get_one(playlist_id)
        except SpotifyAPIError:
            return None
        
        track_urls = []
        for track in playlist['tracks']['items']:
            if track['track']:
                track_urls.append(track['track']['external_urls']['spotify'])

        try:
            playlist_thumbnail = playlist['images'][0]['url']
        except:
            playlist_thumbnail = 'https://i.ytimg.com/vi_webp/nonexist/maxresdefault.webp'
        
        return TrackList(
            name=playlist["name"],
            url=url,
            thumbnail=playlist_thumbnail,
            type="spotify_playlist",
            tracks=track_urls
        )