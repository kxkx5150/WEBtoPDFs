from urllib.parse import urlparse


class LinkNode:
    title = ""
    org_url = None
    dirname = None
    parse_url = None

    prntnode = None
    current_linknodes = None
    child_linknodes = None

    link_check = False
    create_pdf = False

    dlpdf_path = None
    dlimg_path = None

    def __init__(self, page_url, prntnode):
        self.org_url = page_url.rsplit('#', 1)[0]
        self.dirname = page_url.rsplit('/', 1)[0]
        self.parse_url = urlparse(page_url)
        self.prntnode = prntnode

    def append_link_nodes(self, linknodes):
        self.child_linknodes = linknodes

    def set_current_linknodes(self, linknodes):
        self.current_linknodes = linknodes

    def set_title(self, title):
        self.title = title
