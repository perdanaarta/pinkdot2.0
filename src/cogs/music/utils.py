from dataclasses import dataclass
from typing import List
import wavelink


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
    type: str
    tracks: List