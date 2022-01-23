import youtubesearchpython as yts
import youtube_dl


class SearchResult:
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


def youtube_search(search, quick=False):
    search_results = yts.VideosSearch(search, limit=8).result()
    results = []
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        for search_result in dict(search_results).get("result"):
            song_info = ydl.extract_info(search_result.get("link"), download=False)  # TODO make this parallel
            play_urls_filtered = list(filter(lambda format:
                                             format.get("format_note") == "tiny" and format.get("acodec") == "opus",
                                             song_info.get("formats")))
            play_urls_sorted = list(sorted(play_urls_filtered, key=lambda format: format.get("abr")))
            results.append(SearchResult(search_result, play_urls_sorted[-1].get("url")))
            if quick:
                break
    return results


def simple_search(search):
    return youtube_search(search, quick=True)[0]


def advanced_search(search):
    author = ""  # TODO get from spotify search
    search_results = youtube_search(search)
    search_results_filtered = list(filter(lambda search_result: search_result.title.find(author) != -1, search_results))
    if len(search_results_filtered) > 0:
        return search_results_filtered[0]
    return search_results[0]


if __name__ == '__main__':
    videos = youtube_search("power wolf amen and attack")
    for video in videos:
        print(video.title)
