import glob
import shutil
import sys
import json
import os.path
import platform
import time
import random
import PySimpleGUI as sg
from urllib.parse import urlparse
from multiprocessing import Process
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome import service as fs
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from logging import getLogger, StreamHandler, DEBUG
from utils.link_node import LinkNode
from utils.link_nodes import LinkNodes
from utils import allow_urls, deny_urls, deny_exts, allow_exts

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


def init_selenium(app_options):
    options = webdriver.ChromeOptions()
    pltfrm = platform.system()

    if pltfrm == 'Darwin':
        if app_options['use_profile']:
            options.add_argument('~/Library/Application Support/Google/Chrome')
        app_options['os_downloads_path'] = '~/Downloads'
    elif pltfrm == 'Linux':
        if app_options['use_profile']:
            options.add_argument('~/.config/google-chrome')
        app_options['os_downloads_path'] = '~/Downloads'
    else:
        if app_options['use_profile']:
            options.add_argument('--user-data-dir=' + f'C:{os.sep}Users{os.sep}' + os.environ['USERNAME'] +
                                 f'{os.sep}AppData{os.sep}Local{os.sep}Google{os.sep}Chrome{os.sep}User Data')
        app_options['os_downloads_path'] = f'C:{os.sep}Users{os.sep}' + os.environ['USERNAME'] + f'{os.sep}Downloads'

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
    prefs = {
        "printing.print_preview_sticky_settings.appState": json.dumps(appstate),
        "download.default_directory": app_options['os_downloads_path']
    }
    if app_options['use_translate'] and app_options['translate_src'] and app_options['translate_dist']:
        prefs['translate_whitelists'] = {app_options['translate_src']: app_options['translate_dist']}
        prefs['translate'] = {"enabled": "true"}
    else:
        app_options['use_translate'] = False

    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--proxy-server="direct://"')
    options.add_argument('--proxy-bypass-list=*')
    options.add_argument('--start-maximized')
    options.add_argument('--start-maximized')
    options.add_argument('--kiosk-printing')
    options.add_experimental_option("prefs", prefs)
    return options


def save_pdf(driver, crntnode, app_options):
    if crntnode.org_url in app_options['created_urls']:
        return

    crntnode.tmp_title = "dl_pdf_" + app_options['random'] + '_' + crntnode.filename
    driver.execute_script(f'document.title = "{crntnode.tmp_title}"')
    app_options['created_urls'].append(crntnode.org_url)
    crntnode.create_pdf = True
    driver.execute_script('return window.print()')
    time.sleep(1)
    check_download_pdf(crntnode, app_options)


def check_download_pdf(crntnode, app_options):
    timeout_second = 6
    dldir = app_options['os_downloads_path']
    for i in range(timeout_second + 1):
        dlfilenames = glob.glob(f'{dldir}{os.sep}*.*')
        for fname in dlfilenames:
            if fname.find(crntnode.tmp_title) > -1:
                filename, file_extension = os.path.splitext(fname)
                if file_extension == '.pdf':
                    rename_pdf(crntnode, filename + file_extension, app_options)
                    return

        time.sleep(1)

    files = list(filter(os.path.isfile, glob.glob(f'{dldir}{os.sep}*.*')))
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

    abs_img_dst_path = app_options['pic_dir']
    abs_img_dst_path += f'{os.sep}pdf_' + str(app_options['filename_index']).zfill(5) + r'.png'

    crntnode.dlpdf_path = abs_dst_path
    crntnode.dlimg_path = abs_img_dst_path

    if app_options['store_type'] == 'tree':
        abs_dst_path = create_tree_node(crntnode, fname, app_options)

    try:
        shutil.move(abs_src_path, abs_dst_path)
    except Exception as ex:
        pass

    time.sleep(1)


def create_tree_node(crntnode, fname, app_options):
    urls = crntnode.parse_url.path.split('/')
    urls[0] = crntnode.parse_url.netloc
    if not urls[-1]:
        urls[-1] = 'index.html'

    path = os.path.join(*urls)
    path = app_options['download_dir'] + f'{os.sep}pdf{os.sep}' + path + r'.pdf'
    dirname = path.rsplit(os.sep, 1)[0]
    make_dir(dirname)
    return path


def create_screenshot(driver, abs_img_dst_path):
    driver.save_screenshot(abs_img_dst_path)
    time.sleep(1)


def check_page(driver, crntnode, app_options):
    if crntnode.link_check:
        return

    prntelem = driver.find_element(by=By.XPATH, value=app_options['xpath'])
    elems = prntelem.find_elements(By.XPATH, 'descendant::a[@href]')
    child_linknodes = LinkNodes(crntnode.org_url, crntnode, app_options)

    if prntelem:
        for elem in elems:
            href = elem.get_attribute("href")
            if href:
                lnknod = LinkNode(href, crntnode)
                child_linknodes.check_append(lnknod)
                lnknod.set_current_linknodes(child_linknodes)
                print('check:', href)

    crntnode.link_check = True
    crntnode.append_link_nodes(child_linknodes)


def start(driver, linknodes, crnt_depth, app_options):
    crntnode = linknodes.get_current_node()
    errorflg = False

    try:
        driver.get(crntnode.org_url)
        WebDriverWait(driver, timeout=20).until(
            lambda driver: driver.execute_script('return document.readyState === "complete"')
        )
        print(driver.execute_script('return document.readyState'))
        print('   ' * crnt_depth + 'get   : ' + crntnode.org_url)

    except TimeoutException as ex:
        if crntnode.error_retry < 2:
            crntnode.error_retry += 1
            print('TimeoutException sleep 10')
            time.sleep(10)
            driver.get(crntnode.org_url)
        else:
            errorflg = True

    if not errorflg:
        if app_options['use_translate']:
            time.sleep(7)
        else:
            time.sleep(1)

        crntnode.set_title(driver.title)
        print('   ' * crnt_depth + 'pdf   : ' + crntnode.org_url)
        save_pdf(driver, crntnode, app_options)

        if crntnode.dlimg_path and app_options['use_screenshot']:
            create_screenshot(driver, crntnode.dlimg_path)

        if crnt_depth < app_options['depth']:
            print('   ' * crnt_depth + 'check : ' + crntnode.org_url)
            check_page(driver, crntnode, app_options)

    print('')
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


def make_main_dir(app_options):
    diridx = 0
    dlpath = ''
    dldir = app_options['os_downloads_path']
    while True:
        diridx += 1
        dlpath = f'{dldir}{os.sep}pdf_downloader' + str(diridx)
        if not os.path.exists(dlpath):
            break

    app_options['download_dir'] = dlpath
    app_options['pic_dir'] = 'screenshot'
    make_dir(app_options['download_dir'])
    make_dir(app_options['download_dir'] + f'{os.sep}pdf')
    make_dir(app_options['pic_dir'])


def init(app_options, options):
    chrome_servie = fs.Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=chrome_servie, options=options)
    lnode = LinkNode(app_options['top_url'], None)
    linknodes = LinkNodes(app_options['top_url'], None, app_options)
    linknodes.append_node(lnode)
    lnode.set_current_linknodes(linknodes)
    app_options['root_node'] = lnode

    if linknodes.link_count < 1:
        print('root url error')
        return

    make_main_dir(app_options)

    print('---root')
    start(driver, linknodes, 1, app_options)
    driver.quit()


def create_another_process(app_options):
    options = init_selenium(app_options)
    pid = os.getpid()
    print('process1:' + str(pid))
    p = Process(target=init, args=(app_options, options))
    p.start()


def start_log_tab(window, app_options):
    window['Log'].select()
    app_options['log'] = window['Output'].print
    app_options['log']("Program Start ...", text_color='white', background_color='blue')
    pass


def loop_check_msg(window):
    while True:
        closeflg = False
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == 'Quit':
            closeflg = True
            break

        elif event == 'start_button':
            top_url = values['URL_input']
            if not top_url:
                print('url error')
                continue
            click_start_button(window, values)

    if closeflg:
        window.close()


def click_start_button(window, values):
    top_url = values['URL_input']
    if top_url[-1] == '?':
        top_url = top_url[:-1]
        top_url += '%3F'

    parse_url = urlparse(top_url)
    if not parse_url.path:
        top_url += '/'

    app_options = {
        'top_url': top_url.rsplit('#', 1)[0],
        'top_dir': top_url.rsplit('/', 1)[0],
        'samedomain': values['samedomain_checkbox'],
        'prntcheck': values['parent_checkbox'],
        'xpath': values['Xpath_input'],
        'depth': int(values['depth_combo']),
        'allow_urls': allow_urls.urls,
        'deny_urls': deny_urls.urls,
        'allow_exts': allow_exts.extensions,
        'deny_exts': deny_exts.extensions,
        'download_dir': '',
        'os_downloads_path': '',
        'pic_dir': '',
        'filename_index': 0,
        'root_node': None,
        'created_urls': [],
        'use_profile': values['profile_checkbox'],
        'use_translate': values['gtranslate_checkbox'],
        'translate_src': values['tsrc_combo'],
        'translate_dist': values['tdist_combo'],
        'use_screenshot': False,
        'store_type': values['store_combo'],
        'random': str(random.randint(1000, 9999)),
        'log': None
    }
    sys.setrecursionlimit(int(values['recursion_spin']))
    print('recursionlimit : ', sys.getrecursionlimit())
    window['start_button'].update(disabled=True)
    # create_another_process(app_options)
    start_log_tab(window, app_options)


def create_window():
    title = "Web to PDF"
    sg.theme('Default1')
    t1 = sg.Tab('Options', [
        [sg.Text('URL  '), sg.Input(key='URL_input')],
        [sg.Text('XPath'), sg.Input(default_text='/html/body', key='Xpath_input')],
        [sg.T('', font='any 1')],
        [sg.Checkbox('Same domain only', default=True, key='samedomain_checkbox')],
        [sg.Checkbox('Check parent dirctory', default=True, key='parent_checkbox')],
        [sg.Checkbox('Use chrome profile', default=False, key='profile_checkbox')],
        [sg.T('', font='any 1')],
        [sg.Text('Depth'), sg.Combo(['1', '2', '3', '4', '5', '6', '7', '8', '9'],
                                    default_value='2', key='depth_combo')],
        [sg.Text('Store'), sg.Combo(['tree', 'sequential'], default_value='Tree', key='store_combo')],
        [sg.T('', font='any 1')],
        [sg.Frame('Translate', [
            [sg.Checkbox('Google translate', default=False, key='gtranslate_checkbox')],
            [sg.Text('Src '), sg.Combo(['en', 'fr', 'de', 'ru', 'ja', 'zh'], default_value='en', key='tsrc_combo')],
            [sg.Text('Dist'),
             sg.Combo(['en', 'fr', 'de', 'ru', 'ja', 'zh'], default_value='ja', key='tdist_combo')],
        ])],
        [sg.Spin([i for i in range(1000, 1000000)],
                 initial_value=1000, key='recursion_spin'), sg.Text('Recursion limit')],
        [sg.T('', font='any 1')],
        [sg.Button('Start', size=(24, 2), key='start_button')]
    ])
    t2 = sg.Tab('Log', [
        [sg.Multiline(size=(100, 30), font=('Consolas', 10), key='Output')],
    ])
    # t3 = sg.Tab('Tab3', [
    #     [sg.Text('tab3')]
    # ])

    layout = [
        [sg.TabGroup([[t1, t2]])]
    ]
    return sg.Window(title, layout)


def main(args):
    for root, dirs, files in os.walk("screenshot"):
        for file in files:
            os.remove(os.path.join(root, file))

    window = create_window()
    loop_check_msg(window)


if __name__ == '__main__':
    main(sys.argv[1:])
