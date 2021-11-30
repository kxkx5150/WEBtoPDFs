class LinkNodes:
    page_url = None
    prntnode = None

    samedomain = True
    prntcheck = True

    link_nodes = None
    link_count = 0
    check_index = 0

    def __init__(self, page_url, prntnode, app_options):
        self.page_url = page_url
        self.prntnode = prntnode
        self.samedomain = app_options['samedomain']
        self.prntcheck = app_options['prntcheck']
        self.link_nodes = []

    def check_append(self, lnknod):
        if self.samedomain:
            if lnknod.parse_url.netloc == self.prntnode.parse_url.netloc:
                self.append_node(lnknod)
            else:
                self.append_node(lnknod)

    def append_node(self, lnknod):
        print(lnknod.org_url)
        self.link_nodes.append(lnknod)
        self.link_count += 1

    def get_current_node(self):
        if self.check_index == len(self.link_nodes):
            return None

        return self.link_nodes[self.check_index]

    def inc_check_index(self):
        if self.check_index < self.link_count:
            self.check_index += 1

