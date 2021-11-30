from urllib.parse import urlparse


class LinkNode:
    org_url = None
    dirname = None
    parse_url = None
    prntnode = None
    linknodes = None
    link_check = False
    create_pdf = False

    def __init__(self, page_url, prntnode):
        self.org_url = page_url
        self.dirname = page_url.rsplit('/', 1)[0]
        self.parse_url = urlparse(page_url)
        self.prntnode = prntnode

    def apped_link_nodes(self, linknodes):
        self.linknodes = linknodes


