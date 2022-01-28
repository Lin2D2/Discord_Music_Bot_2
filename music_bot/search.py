import logging

import youtubesearchpython as yts
import youtube_dl


class SearchResultType:
    def __init__(self, dict_search_result, play_url):
        self.id = dict_search_result.get('id')
        self.title = dict_search_result.get('title')
        self.duration = dict_search_result.get('duration')
        self.thumbnail_url = dict_search_result.get('thumbnails')[0].get("url")
        self.channel = dict_search_result.get("channel").get("name")
        self.url = dict_search_result.get("link")
        self.play_url = play_url


ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }


class SearchHandler:
    def __init__(self):
        self.cache_limit = 500
        self.search_cache = {}
        # NOTE store format {url: SearchResultType}

    def cache_limit_check(self):
        logging.info(f"cache_limit_check")
        if len(self.search_cache.values()) > self.cache_limit:
            marked_for_delete = list(self.search_cache.keys())
            marked_for_delete.reverse()
            marked_for_delete = marked_for_delete[self.cache_limit-1:]
            logging.info(f"trimming cache: {len(self.search_cache.values()) - self.cache_limit} "
                         f"entries ready for deletion")
            for key in marked_for_delete:
                self.search_cache.pop(key)

    def youtube_search(self, search, quick=False):
        search_results = yts.VideosSearch(search, limit=8).result()
        results = []
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:  # TODO error handling
            for search_result in dict(search_results).get("result"):
                link = search_result.get("link")
                if link in self.search_cache.keys():
                    logging.info(f"{link} found in cache")
                    result = self.search_cache.get(link)
                else:
                    logging.info(f"getting {link} info from youtube")
                    song_info = ydl.extract_info(link, download=False)  # TODO make this parallel
                    play_urls_filtered = list(filter(lambda format_object:
                                                     format_object.get("format_note") == "tiny" and
                                                     format_object.get("acodec") == "opus",
                                                     song_info.get("formats")))
                    play_urls_sorted = list(sorted(play_urls_filtered, key=lambda format_object: format_object.get("abr")))
                    try:
                        result = SearchResultType(search_result, play_urls_sorted[-1].get("url"))
                    except IndexError:
                        try:
                            result = SearchResultType(search_result, play_urls_filtered[0].get("url"))
                        except IndexError:
                            song_info = ydl.extract_info(link, download=False)
                            result = SearchResultType(search_result, song_info.get("formats")[0].get("url"))
                    self.search_cache.update({link: result})
                results.append(result)
                if quick:
                    break
        return results

    def simple_search(self, search):
        return self.youtube_search(search, quick=True)[0]

    def advanced_search(self, search):
        author = ""  # TODO get from spotify search
        search_results = self.youtube_search(search)
        search_results_filtered = list(filter(lambda search_result: search_result.title.find(author) != -1,
                                              search_results))
        if len(search_results_filtered) > 0:
            return search_results_filtered[0]
        return search_results[0]


if __name__ == '__main__':
    search_handler = SearchHandler()
    videos = search_handler.youtube_search("power wolf amen and attack")
    for video in videos:
        print(video.title)
