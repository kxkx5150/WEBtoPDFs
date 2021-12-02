import os


class LinkNodes:
    page_url = None
    prntnode = None

    samedomain = True
    prntcheck = True

    link_nodes = None
    link_count = 0
    check_index = 0

    allow_urls = {}
    deny_urls = {}

    def __init__(self, page_url, prntnode, app_options):
        self.page_url = page_url
        self.prntnode = prntnode

        self.samedomain = app_options['samedomain']
        self.prntcheck = app_options['prntcheck']
        self.allow_urls = app_options['allow_urls']
        self.deny_urls = app_options['deny_urls']

        self.link_nodes = []

    def check_append(self, lnknod):
        ext = os.path.splitext(lnknod.org_url)



        if len(self.allow_urls) > 0:
            for aurl in self.allow_urls:
                if aurl[-1] == '/':
                    aurl = aurl.rsplit('/', 1)[0]
                    if lnknod.dirname == aurl:
                        self.append_node(lnknod)
                else:
                    if lnknod.org_url == aurl:
                        self.append_node(lnknod)
        else:
            if self.samedomain:
                if lnknod.parse_url.netloc == self.prntnode.parse_url.netloc:
                    self.append_node(lnknod)
            else:
                self.append_node(lnknod)

    def append_node(self, lnknod):
        if len(self.deny_urls) > 0:
            for durl in self.deny_urls:
                if durl[-1] == '/':
                    durl = durl.rsplit('/', 1)[0]
                    if lnknod.dirname == durl:
                        return
                else:
                    if lnknod.org_url == durl:
                        return

        for lnode in self.link_nodes:
            if lnode.org_url == lnknod.org_url:
                return

        self.link_nodes.append(lnknod)
        self.link_count += 1

    def get_current_node(self):
        if self.check_index == len(self.link_nodes):
            return None
        else:
            return self.link_nodes[self.check_index]

    def inc_check_index(self):
        if self.check_index < self.link_count:
            self.check_index += 1

