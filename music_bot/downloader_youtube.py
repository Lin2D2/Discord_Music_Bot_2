import youtube_dl


def my_hook(d):
    if d['status'] == 'finished':
        print('Done downloading, now converting ...')
        # TODO show this to user


def download(url, path):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'progress_hooks': [my_hook],
        'outtmpl': path,
    }
    with youtube_dl.YoutubeDL(ydl_opts) as yt_dl:
        yt_dl.download([url])
