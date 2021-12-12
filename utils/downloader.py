import os
import sys
import time

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

    def start(self):
        if self.start_index < len(self.url_lists):
            self.download_file(self.url_lists[self.start_index])
            self.start_index += 1
            val = (self.start_index / len(self.url_lists)) * 100
            self.show_progress(val)
            time.sleep(0.2)
            self.start()

        else:
            self.show_progress(100)

    def show_progress(self, val):
        self.window['_PROGRESS_BAR_'].UpdateBar(val)

    def download_file(self, furl):
        fname = furl[furl.rfind('/') + 1:]
        file_name = self.default_dldir + os.sep + fname
        link = self.url_lists[self.start_index]

        with open(file_name, "wb") as f:
            print("Downloading %s" % file_name)
            response = requests.get(link, stream=True)
            total_length = response.headers.get('content-length')

            if total_length is None:  # no content length header
                f.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in response.iter_content(chunk_size=4096):
                    dl += len(data)
                    f.write(data)
                    done = int(50 * dl / total_length)
                    sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50 - done)))
                    sys.stdout.flush()
