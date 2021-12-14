import os
import re
import threading
import time
import urllib
from urllib.parse import urlparse

import requests


class Downloader:
    url_lists = []
    start_index = 0
    default_dldir = None
    window = None

    def __init__(self, window, txt, default_dldir, start):
        self.window = window
        self.default_dldir = default_dldir
        self.start_index = start

        lists = txt.splitlines()
        for lst in lists:
            lst.strip()
            if lst.find(r'http:') == 0 or lst.find(r'https:') == 0:
                self.url_lists.append(lst)

        diridx = 0
        while True:
            diridx += 1
            dlpath = f'{self.default_dldir}{os.sep}downloader' + str(diridx)
            if not os.path.exists(dlpath):
                os.makedirs(dlpath, exist_ok=True)
                self.default_dldir = dlpath
                break

    def create_thread(self):
        self.window['_DOWNLOAD_ALL_'].update(disabled=True)
        threading.Thread(target=self.start, args=(), daemon=True).start()

    def start(self):
        if self.start_index < len(self.url_lists):
            self.download_file(self.url_lists[self.start_index])
            self.start_index += 1
            val = (self.start_index / len(self.url_lists)) * 100
            self.show_total_progress(val)
            self.show_progress(0)
            time.sleep(0.2)
            self.start()

        else:
            self.show_total_progress(100)
            self.window['_DOWNLOAD_ALL_'].update(disabled=False)

    def show_progress(self, val):
        self.window['_PROGRESS_BAR_'].UpdateBar(val)

    def show_total_progress(self, val):
        self.window['_TOTAL_PROGRESS_BAR_'].UpdateBar(val)

    def download_file(self, file_url):
        parse_url = urlparse(file_url)
        fname = urllib.parse.unquote(parse_url.path[parse_url.path.rfind('/') + 1:])
        fname = os.path.basename(fname)
        file_name = self.default_dldir + os.sep + fname
        re.sub(r'[\\/:*?"<>|]+','',file_name)
        headers = requests.head(file_url).headers

        try:
            total_length = int(headers["content-length"])
        except Exception as e:
            print(e)
            total_length = None

        response = requests.get(file_url, stream=True)

        try:
            with open(file_name, "wb") as f:
                if total_length is None:
                    f.write(response.content)
                else:
                    dl = 0
                    total_length = int(total_length)
                    for data in response.iter_content(chunk_size=4096):
                        dl += len(data)
                        f.write(data)
                        done = dl / total_length * 100
                        self.show_progress(done)
        except FileNotFoundError as e:
            print("FileNotFoundError", e)
            print(file_url)
            print(file_name)

        except Exception as e:
            print(e)

