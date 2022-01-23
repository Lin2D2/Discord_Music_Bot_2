import time

from tinydb import TinyDB, where

import downloader_youtube


class SongType:
    def __init__(self, search_result=None, filename=None, from_dict=None):
        if search_result:
            self.id = search_result.id
            self.title = search_result.title
            self.duration = search_result.duration
            self.thumbnail_url = search_result.thumbnail_url
            self.url = search_result.url
            self.filename = filename
            self.created = time.time()
        else:
            self.id = from_dict.get('id')
            self.title = from_dict.get('title')
            self.duration = from_dict.get('duration')
            self.thumbnail_url = from_dict.get('thumbnail_url')
            self.url = from_dict.get('url')
            self.filename = from_dict.get('filename')
            self.created = from_dict.get('created')

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "duration": self.duration,
            "thumbnail_url": self.thumbnail_url,
            "url": self.url,
            "filename": self.filename,
            "created": self.created,
        }


class StorageManager:
    def __init__(self):
        self.db = TinyDB("storage_manager.db")
        # self.disk_usage = 0  # TODO
        self.songs = [SongType(from_dict=song) for song in self.db.all()]

    def request_song(self, search):
        result = self.db.search(where("url") == search.url)
        if len(result) == 0:
            filename = f"downloads/{time.time()}.mp3"
            downloader_youtube.download(search.url, filename)
            result = SongType(search_result=search, filename=filename)
            self.db.insert(result.to_dict())
            return result
        return result
