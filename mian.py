import glob
import shutil
import sys
import json
import os.path
import platform
import time

from selenium import webdriver
from selenium.webdriver.chrome import service as fs
# from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from logging import getLogger, StreamHandler, DEBUG
from utils.link_node import LinkNode
from utils.link_nodes import LinkNodes
from utils import allow_urls, deny_urls, deny_exts

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False
root_node = None
file_name_index = 0

options = webdriver.ChromeOptions()
pltfrm = platform.system()
download_folder = ''
if pltfrm == 'Darwin':
    options.add_argument('~/Library/Application Support/Google/Chrome')
    download_folder = '~/Downloads'
elif pltfrm == 'Linux':
    options.add_argument('~/.config/google-chrome')
    download_folder = '~/Downloads'
else:
    options.add_argument('--user-data-dir=C:\\Users\\' + os.environ['USERNAME'] +
                         '\\AppData\\Local\\Google\\Chrome\\User Data')
    download_folder = 'C:\\Users\\' + os.environ['USERNAME'] + '\\Downloads'

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
    "isCssBackgroundEnabled": True,
    "isHeaderFooterEnabled": False
}
options.add_argument('--disable-gpu')
options.add_argument('--disable-extensions')
options.add_argument('--proxy-server="direct://"')
options.add_argument('--proxy-bypass-list=*')
options.add_argument('--start-maximized')
options.add_argument('--start-maximized')
options.add_argument('--kiosk-printing')
options.add_experimental_option("prefs",
                                {"printing.print_preview_sticky_settings.appState": json.dumps(appState),
                                 "download.default_directory": download_folder}
                                )


def save_pdf(driver, crntnode):
    crntnode.create_pdf = True
    driver.execute_script('return window.print()')
    check_download_pdf(driver, crntnode)


def check_download_pdf(driver, crntnode):
    timeout_second = 10
    for i in range(timeout_second + 1):
        dlfilenames = glob.glob(f'{download_folder}\\*.*')
        for fname in dlfilenames:
            if fname.find(crntnode.title) > -1:
                filename, file_extension = os.path.splitext(fname)
                if file_extension == '.pdf':
                    rename_pdf(fname, crntnode)

        time.sleep(1)


def rename_pdf(fname, crntnode):
    global file_name_index
    file_name_index = file_name_index+1
    os.rename(fname, download_folder + '\\pdf_downloader\\' + 'pdf_' + str(file_name_index).zfill(5) + '.pdf')


def check_page(driver, crntnode, app_options):
    prntelem = driver.find_element(by=By.XPATH, value=app_options['xpath'])
    elems = prntelem.find_elements(By.XPATH, 'descendant::*[@href]')
    child_linknodes = LinkNodes(crntnode.org_url, crntnode, app_options)

    if prntelem:
        for elem in elems:
            href = elem.get_attribute("href")
            lnknod = LinkNode(href, crntnode)
            child_linknodes.check_append(lnknod)
            lnknod.set_current_linknodes(child_linknodes)

    crntnode.link_check = True
    crntnode.append_link_nodes(child_linknodes)


def start(driver, linknodes, crnt_depth, app_options):
    crntnode = linknodes.get_current_node()
    driver.get(crntnode.org_url)
    WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located)
    crntnode.set_title(driver.title)
    print('   ' * crnt_depth + crntnode.org_url)
    save_pdf(driver, crntnode)

    if crnt_depth < app_options['depth']:
        check_page(driver, crntnode, app_options)
    linknodes.inc_check_index()

    if crnt_depth < app_options['depth']:
        if crntnode.child_linknodes.link_count > 0:
            targetnode = crntnode.child_linknodes.get_current_node()
            if targetnode:
                crnt_depth += 1
                print('---down')
                start(driver, crntnode.child_linknodes, crnt_depth, app_options)
            else:
                next_linknode(driver, linknodes, crnt_depth, app_options)

        else:
            next_linknode(driver, linknodes, crnt_depth, app_options)

    elif crnt_depth == app_options['depth']:
        next_linknode(driver, linknodes, crnt_depth, app_options)


def next_linknode(driver, linknodes, crnt_depth, app_options):
    crntnode = linknodes.get_current_node()
    if crntnode:
        print('next')
        start(driver, linknodes, crnt_depth, app_options)
    else:
        lnknds = linknodes
        while True:
            print('---up')
            crnt_depth -= 1
            if crnt_depth < 2:
                print('---root')
                break

            prntnode = lnknds.prntnode
            lnknds = prntnode.current_linknodes
            crntnode = lnknds.get_current_node()
            if crntnode:
                start(driver, lnknds, crnt_depth, app_options)
                break


def make_dir(dirpath):
    if not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)


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

    make_dir(download_folder + '\\pdf_downloader')
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

    prntcheck = input('check parent dirctory ? (y or n)Default y : ')
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
        'top_url': top_url.rsplit('#', 1)[0],
        'top_dir': top_url.rsplit('/', 1)[0],
        'samedomain': samedomain,
        'prntcheck': prntcheck,
        'xpath': xpath,
        'depth': depth,
        'allow_urls': allow_urls.urls,
        'deny_urls': deny_urls.urls,
        'deny_exts': deny_exts.extensions
    }

    init(top_url, app_options)


if __name__ == '__main__':
    main(sys.argv[1:])
