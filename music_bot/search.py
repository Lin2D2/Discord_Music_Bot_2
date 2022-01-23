import youtubesearchpython as yts


class SearchResult:
    def __init__(self, dict_search_result):
        self.id = dict_search_result.get('id')
        self.title = dict_search_result.get('title')
        self.duration = dict_search_result.get('duration')
        self.thumbnail_url = dict_search_result.get('thumbnails')[0].get("url")
        self.channel = dict_search_result.get("channel").get("name")
        self.url = dict_search_result.get("link")


def youtube_search(search):
    search_results = yts.VideosSearch(search, limit=8).result()
    return [SearchResult(result) for result in dict(search_results).get("result")]


def simple_search(search):
    return youtube_search(search)[0]


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
