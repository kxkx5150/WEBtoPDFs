import sys
import time
import json
import os.path
import platform
from selenium import webdriver
from selenium.webdriver.chrome import service as fs
# from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from logging import getLogger, StreamHandler, DEBUG
from link_node import LinkNode
from link_nodes import LinkNodes
import allow_urls
import deny_urls

options = webdriver.ChromeOptions()
options.add_argument('--disable-gpu')
options.add_argument('--disable-extensions')
options.add_argument('--proxy-server="direct://"')
options.add_argument('--proxy-bypass-list=*')
options.add_argument('--start-maximized')
options.add_argument('--start-maximized')
pltfrm = platform.system()
if pltfrm == 'Darwin':
    options.add_argument('~/Library/Application Support/Google/Chrome')
elif pltfrm == 'Linux':
    options.add_argument('~/.config/google-chrome')
else:
    options.add_argument('--user-data-dir=C:\\Users\\' + os.environ['USERNAME'] +
                         '\\AppData\\Local\\Google\\Chrome\\User Data')
appState = {
    "recentDestinations": [
        {
            "id": "Save as PDF",
            "origin": "local",
            "account": ""
        }
    ],
    "selectedDestinationId": "Save as PDF",
    "version": 2,
    "pageSize": 'A4',
    "isCssBackgroundEnabled": True
}
options.add_experimental_option("prefs", {
    "printing.print_preview_sticky_settings.appState": json.dumps(appState),
    "download.default_directory": '~/Downloads'
})
options.add_argument('--kiosk-printing')

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False
root_node = None


def save_pdf(driver, crntnode):
    crntnode.create_pdf = True
    driver.execute_script('window.print()')
    time.sleep(7)


def check_page(driver, crntnode, app_options):
    driver.implicitly_wait(5)
    prntelem = driver.find_element(by=By.XPATH, value=app_options['xpath'])
    elems = prntelem.find_elements(By.XPATH, 'descendant::*[@href]')
    child_linknodes = LinkNodes(crntnode.org_url, crntnode, app_options)

    if prntelem:
        for elem in elems:
            href = elem.get_attribute("href")
            if href.find('mailto:') == 0:
                continue
            lnknod = LinkNode(href, crntnode)
            child_linknodes.check_append(lnknod)
            lnknod.set_current_linknodes(child_linknodes)

    crntnode.link_check = True
    crntnode.append_link_nodes(child_linknodes)


def start(driver, linknodes, crnt_depth, app_options):
    crntnode = linknodes.get_current_node()
    driver.get(crntnode.org_url)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_all_elements_located)
    save_pdf(driver, crntnode)

    if crnt_depth < app_options['depth']:
        check_page(driver, crntnode, app_options)
    linknodes.inc_check_index()

    if crnt_depth < app_options['depth']:
        if crntnode.child_linknodes.link_count > 0:
            targetnode = crntnode.child_linknodes.get_current_node()
            if targetnode:
                crnt_depth += 1
                print(' ' * crnt_depth + 'down : ' + targetnode.org_url)
                start(driver, crntnode.child_linknodes, crnt_depth, app_options)
            else:
                next_linknode(driver, linknodes, crnt_depth, app_options)

        else:
            next_linknode(driver, linknodes, crnt_depth, app_options)

    elif crnt_depth == app_options['depth']:
        next_linknode(driver, linknodes, crnt_depth, app_options)

    else:
        pass


def next_linknode(driver, linknodes, crnt_depth, app_options):
    crntnode = linknodes.get_current_node()
    if crntnode:
        print(' ' * crnt_depth + 'next : ' + crntnode.org_url)
        start(driver, linknodes, crnt_depth, app_options)
    else:
        lnknds = linknodes
        while True:
            crnt_depth -= 1
            if crnt_depth < 2:
                break

            prntnode = lnknds.prntnode
            lnknds = prntnode.current_linknodes
            crntnode = lnknds.get_current_node()
            if crntnode:
                start(driver, lnknds, crnt_depth, app_options)
                break


def init(top_url, app_options):
    chrome_servie = fs.Service(executable_path="chromedriver.exe")
    driver = webdriver.Chrome(service=chrome_servie, options=options)

    global root_node
    root_node = LinkNode(top_url, None)
    linknodes = LinkNodes(top_url, None, app_options)
    linknodes.append_node(root_node)
    root_node.set_current_linknodes(linknodes)
    if linknodes.link_count < 1:
        print('url error')
        return

    start(driver, linknodes, 1, app_options)
    driver.quit()


def main(args):
    top_url = ''
    if len(args):
        top_url = args[0]
    if not top_url:
        top_url = input('URL : ')
    if not top_url:
        print('url error')
        return

    samedomain = input('same domain only ? (y or n)Default y : ')
    if samedomain == 'n':
        samedomain = False
    else:
        samedomain = True

    prntcheck = input('parent dirctory ? (y or n)Default y : ')
    if prntcheck == 'n':
        prntcheck = False
    else:
        prntcheck = True

    xpath = input('links in target element ? (XPATH)Default /html/body : ')
    if not xpath:
        xpath = '/html/body'

    depth = input('Depth ? Default 2 : ')
    try:
        depth = int(depth)
    except ValueError:
        depth = 2

    app_options = {
        'samedomain': samedomain,
        'prntcheck': prntcheck,
        'xpath': xpath,
        'depth': depth,
        'allow_urls': allow_urls.urls,
        'deny_urls': deny_urls.urls
    }

    init(top_url, app_options)


if __name__ == '__main__':
    main(sys.argv[1:])

