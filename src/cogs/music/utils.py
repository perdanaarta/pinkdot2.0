from dataclasses import dataclass
from typing import Generator, List
import wavelink
from wavelink.ext import spotify

@dataclass
class Track:
    title: str
    url: str
    thumbnail: str
    wavelink: wavelink.YouTubeTrack


class YouTubeTrackList:
    def __init__(self, name: str, url: str, thumbnail: str, tracks: List) -> None:
        self.name = name
        self.url = url
        self.thumbnail = thumbnail
        self.tracks = tracks

    async def iterator(self):
        async for track in self.tracks:
            yield track

class SpotifyTrackList:
    def __init__(self, name: str, url: str, thumbnail: str, type: str) -> None:
        self.name = name
        self.url = url
        self.thumbnail = thumbnail
        self.type = type

    async def iterator(self):
        if self.type == 'album':
            async for track in spotify.SpotifyTrack.iterator(
                query=self.url, 
                type=spotify.SpotifySearchType.album
            ):
                yield track
        
        elif self.type == 'playlist':
            async for track in spotify.SpotifyTrack.iterator(
                query=self.url, 
                type=spotify.SpotifySearchType.playlist
            ):
                yield track
        