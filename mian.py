import glob
import shutil
import sys
import json
import os.path
import platform
import time
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome import service as fs
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
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
download_folder = ''


def init_selenium():
    global download_folder
    options = webdriver.ChromeOptions()
    pltfrm = platform.system()
    if pltfrm == 'Darwin':
        options.add_argument('~/Library/Application Support/Google/Chrome')
        download_folder = '~/Downloads'
    elif pltfrm == 'Linux':
        options.add_argument('~/.config/google-chrome')
        download_folder = '~/Downloads'
    else:
        options.add_argument('--user-data-dir=' + f'C:{os.sep}Users{os.sep}' + os.environ['USERNAME'] +
                             f'{os.sep}AppData{os.sep}Local{os.sep}Google{os.sep}Chrome{os.sep}User Data')
        download_folder = f'C:{os.sep}Users{os.sep}' + os.environ['USERNAME'] + f'{os.sep}Downloads'

    appstate = {
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
    options.add_experimental_option(
        "prefs",
        {
            "printing.print_preview_sticky_settings.appState": json.dumps(appstate),
            "download.default_directory": download_folder
        }
    )
    return options


def save_pdf(driver, crntnode, app_options):
    if crntnode.org_url in app_options['created_urls']:
        return
    app_options['created_urls'].append(crntnode.org_url)
    crntnode.create_pdf = True
    driver.execute_script('return window.print()')
    check_download_pdf(crntnode, app_options)
    time.sleep(1)
    if crntnode.dlimg_path:
        create_screenshot(driver, crntnode.dlimg_path)
    time.sleep(1)


def check_download_pdf(crntnode, app_options):
    timeout_second = 7
    for i in range(timeout_second + 1):
        dlfilenames = glob.glob(f'{download_folder}{os.sep}*.*')
        for fname in dlfilenames:
            if fname.find(crntnode.title) > -1:
                filename, file_extension = os.path.splitext(fname)
                if file_extension == '.pdf':
                    rename_pdf(crntnode, filename + file_extension, app_options)
                    return

        time.sleep(1)

    files = list(filter(os.path.isfile, glob.glob(f'{download_folder}{os.sep}*.*')))
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    for f in files:
        fn, fe = os.path.splitext(f)
        if fe == '.pdf':
            rename_pdf(crntnode, fn + fe, app_options)
            return


def rename_pdf(crntnode, fname, app_options):
    app_options['filename_index'] += 1
    abs_src_path = fname
    if abs_src_path.find(r' '):
        if abs_src_path.find(r'\ '):
            abs_src_path.replace(r'\\ ', r'\ ')
        else:
            abs_src_path.replace(r' ', r'\ ')
    abs_dst_path = app_options['download_dir']
    abs_dst_path += f'{os.sep}pdf{os.sep}pdf_' + str(app_options['filename_index']).zfill(5) + r'.pdf'

    abs_img_dst_path = app_options['download_dir']
    abs_img_dst_path += f'{os.sep}screenshot{os.sep}pdf_' + str(app_options['filename_index']).zfill(5) + r'.png'

    crntnode.dlpdf_path = abs_dst_path
    crntnode.dlimg_path = abs_img_dst_path

    shutil.move(abs_src_path, abs_dst_path)
    time.sleep(1)


def create_screenshot(driver, abs_img_dst_path):
    driver.save_screenshot(abs_img_dst_path)


def check_page(driver, crntnode, app_options):
    if crntnode.link_check:
        return
    prntelem = driver.find_element(by=By.XPATH, value=app_options['xpath'])
    elems = prntelem.find_elements(By.XPATH, 'descendant::a[@href]')
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
    WebDriverWait(driver, 15).until(expected_conditions.presence_of_all_elements_located)
    crntnode.set_title(driver.title)
    print('   ' * crnt_depth + crntnode.org_url)
    save_pdf(driver, crntnode, app_options)

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


def init(top_url, app_options, options):
    chrome_servie = fs.Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=chrome_servie, options=options)

    lnode = LinkNode(top_url, None)
    linknodes = LinkNodes(top_url, None, app_options)
    linknodes.append_node(lnode)
    lnode.set_current_linknodes(linknodes)
    app_options['root_node'] = lnode

    if linknodes.link_count < 1:
        print('url error')
        return

    diridx = 0
    while True:
        diridx += 1
        if not os.path.exists('pdf_downloader' + str(diridx)):
            break

    app_options['download_dir'] = 'pdf_downloader' + str(diridx)
    make_dir(app_options['download_dir'])
    make_dir(app_options['download_dir'] + f'{os.sep}pdf')
    make_dir(app_options['download_dir'] + f'{os.sep}screenshot')

    print('---root')
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
    if top_url[-1] == '?':
        top_url = top_url[:-1]
        top_url += '%3F'

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

    recus = input('recursionlimit ? Default 1000 : ')
    try:
        recus = int(recus)
    except ValueError:
        recus = 1000

    sys.setrecursionlimit(recus)
    print(sys.getrecursionlimit())

    app_options = {
        'top_url': top_url.rsplit('#', 1)[0],
        'top_dir': top_url.rsplit('/', 1)[0],
        'samedomain': samedomain,
        'prntcheck': prntcheck,
        'xpath': xpath,
        'depth': depth,
        'allow_urls': allow_urls.urls,
        'deny_urls': deny_urls.urls,
        'deny_exts': deny_exts.extensions,
        'download_dir': download_folder,
        'filename_index': 0,
        'root_node': None,
        'created_urls': []
    }
    options = init_selenium()
    init(top_url, app_options, options)


if __name__ == '__main__':
    main(sys.argv[1:])
