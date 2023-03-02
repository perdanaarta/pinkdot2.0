from dataclasses import dataclass
import wavelink
from .utils import Track, TrackList


class YouTubeSearch():
    async def search(query: str, amount: int=5) -> list[Track]:
        wv_list = []
        for wv in (await wavelink.YouTubeMusicTrack.search(query))[:amount]:
            wv_list.append(
                Track(
                    title = wv.title,
                    url = wv.uri,
                    thumbnail = wv.thumbnail,
                    wavelink = wv
                )
            )
        return wv_list
    
    async def get_video(url: str):
        wv = await wavelink.YouTubeTrack.search(query=url, return_first=True)
        return Track(
            title= wv.title,
            url= wv.uri,
            thumbnail= wv.thumbnail,
            wavelink= wv
        )
    
    async def get_playlist(url: str):
        wv: wavelink.YouTubePlaylist = await wavelink.YouTubePlaylist.search(url)

        tracks = []
        for tr in wv.tracks:
            tracks.append(
                Track(
                    title = tr.title,
                    url = tr.uri,
                    thumbnail = tr.thumbnail,
                    wavelink = tr
                )
            )

        return TrackList(
            name = wv.name,
            url = wv.uri,
            type = "youtube_playlist",
            tracks = tracks
        )