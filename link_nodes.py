class LinkNodes:
    page_url = None
    prntnode = None
    samedomain = True
    prntcheck = True
    link_nodes = []
    link_count = 0

    def __init__(self, page_url, prntnode, samedomain, prntcheck):
        self.page_url = page_url
        self.prntnode = prntnode
        self.samedomain = samedomain
        self.prntcheck = prntcheck

    def check_append(self, lnknod):
        pass
        if self.samedomain:
            if lnknod.parse_url.netloc == self.prntnode.parse_url.netloc:
                self.append_node(lnknod)
            else:
                self.append_node(lnknod)

    def append_node(self, lnknod):
        print(lnknod.org_url)
        self.link_nodes.append(lnknod)
        self.link_count += 1
