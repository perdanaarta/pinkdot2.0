from dataclasses import dataclass
from typing import List
import wavelink

# @dataclass
# class SpotifyTrack:


@dataclass
class Track:
    title: str
    url: str
    thumbnail: str
    wavelink: wavelink.YouTubeTrack

@dataclass
class TrackList:
    name: str
    url: str
    thumbnail: str
    type: str
    tracks: List