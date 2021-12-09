import io
import sys

import PIL
import fitz
import json
import time
import glob
import random
import shutil
import os.path
import platform
import threading
from PIL import Image
import PySimpleGUI as sg
from urllib.parse import urlparse
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
from utils.country import cconde

window = None
treedata = None
open_dirs = []
logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False
stop_thread = False
pltfrm = platform.system()
user_dir = ''
default_dldir = r'~/Downloads'

if pltfrm == 'Darwin':
    user_dir = r'~/Library/Application Support/Google/Chrome'
elif pltfrm == 'Windows':
    user_dir = f'C:{os.sep}Users{os.sep}' + os.environ['USERNAME'] + \
               f'{os.sep}AppData{os.sep}Local{os.sep}Google{os.sep}Chrome{os.sep}User Data'
    default_dldir = f'C:{os.sep}Users{os.sep}' + os.environ['USERNAME'] + f'{os.sep}Downloads'
else:
    user_dir = r'~/.config/google-chrome'


def init_selenium(app_options):
    global user_dir
    global default_dldir
    options = webdriver.ChromeOptions()
    if app_options['use_profile']:
        options.add_argument('--user-data-dir=' + user_dir)
    app_options['os_downloads_path'] = default_dldir

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
                app_options['log']('check:', href, text_color='gray')
                print('check:', href)

    crntnode.link_check = True
    crntnode.append_link_nodes(child_linknodes)


def start(driver, linknodes, crnt_depth, app_options):
    if stop_thread:
        app_options['window']['Log'].select()
        app_options['log']("stop thread", text_color='white', background_color='red')
        print("stop thread")
        return

    crntnode = linknodes.get_current_node()
    errorflg = False

    try:
        driver.get(crntnode.org_url)
        WebDriverWait(driver, timeout=20).until(
            lambda driver: driver.execute_script('return document.readyState === "complete"')
        )
        rstat = driver.execute_script('return document.readyState')
        app_options['log'](rstat)
        app_options['log']('   ' * crnt_depth + 'get   : ' + crntnode.org_url, text_color='blue')

        print(rstat)
        print('   ' * crnt_depth + 'get   : ' + crntnode.org_url)

    except TimeoutException as ex:
        if crntnode.error_retry < 2:
            crntnode.error_retry += 1
            app_options['log']('TimeoutException sleep 10', text_color='white', background_color='red')
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
        app_options['log']('   ' * crnt_depth + 'pdf   : ' + crntnode.org_url, text_color='blue')

        print('   ' * crnt_depth + 'pdf   : ' + crntnode.org_url)
        save_pdf(driver, crntnode, app_options)

        if crntnode.dlimg_path and app_options['use_screenshot']:
            create_screenshot(driver, crntnode.dlimg_path)

        if crnt_depth < app_options['depth']:
            app_options['log']('   ' * crnt_depth + 'check : ' + crntnode.org_url, text_color='blue')

            print('   ' * crnt_depth + 'check : ' + crntnode.org_url)
            check_page(driver, crntnode, app_options)

    app_options['log']('')
    print('')
    linknodes.inc_check_index()

    if crnt_depth < app_options['depth']:
        if crntnode.child_linknodes.link_count > 0:
            targetnode = crntnode.child_linknodes.get_current_node()
            if targetnode:
                crnt_depth += 1
                app_options['log']('---down', text_color='deep pink')
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
            app_options['log']('---up', text_color='deep pink')
            print('---up')
            crnt_depth -= 1
            if crnt_depth < 2:
                app_options['log']('---root')
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


def init(app_options, options, window):
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
    app_options['log']("---root", text_color='blue')

    print('---root')
    start(driver, linknodes, 1, app_options)
    driver.quit()


def create_another_process(app_options, window):
    options = init_selenium(app_options)
    threading.Thread(target=init, args=(app_options, options, window,), daemon=True).start()


def start_log_tab(window, app_options):
    window['Log'].select()
    app_options['log']("Program Start ...")
    pass


def loop_check_msg(window):
    while True:
        closeflg = False
        event, values = window.read()
        pass

        if event == sg.WIN_CLOSED or event == 'Quit':
            closeflg = True
            break

        elif event == '_START_':
            top_url = values['URL_input']
            if not top_url:
                continue
            click_start_button(window, values)

        elif event == '_STOP_':
            click_stop_button()

        elif event == '_TREE_':
            values = values['_TREE_']
            if len(values) < 1:
                continue
            val = values[0]
            if os.path.isfile(val):
                path, ext = os.path.splitext(val)
                if ext == '.pdf':
                    refresh_pdf_viewer(val)

        elif event == '_REFRESH_':
            refresh_folder_tree()

        elif event == '_DELETE_':
            values = values['_TREE_']
            delete_tree_node(window, values[0])

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
        'log': window['Output'].print,
        'window': window
    }
    sys.setrecursionlimit(int(values['recursion_spin']))
    print('recursionlimit : ', sys.getrecursionlimit())

    global stop_thread
    stop_thread = False
    window['_START_'].update(disabled=True)
    start_log_tab(window, app_options)
    create_another_process(app_options, window)


def click_stop_button():
    global stop_thread
    stop_thread = True


def read_pdf(pdfpath=f'pdf{os.sep}blank.pdf'):
    def get_page(pno):
        dlist = dlist_tab[pno]
        if not dlist:
            dlist_tab[pno] = doc[pno].getDisplayList()
            dlist = dlist_tab[pno]
        r = dlist.rect
        pix = dlist.getPixmap(alpha=False)
        return pix.getPNGData()

    doc = fitz.open(pdfpath)
    page_count = len(doc)
    dlist_tab = [None] * page_count
    cur_page = 0
    return get_page(cur_page)


def create_folder_tree(dir_path):
    treedata = sg.TreeData()
    folder_icon = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS' \
                  b'3X78AAABnUlEQVQ4y8WSv2rUQRSFv7vZgJFFsQg2EkWb4AvEJ8hqKVilSmFn3iNvIAp21' \
                  b'oIW9haihBRKiqwElMVsIJjNrprsOr/5dyzml3UhEQIWHhjmcpn7zblw4B9lJ8Xag9mlmQb' \
                  b'3AJzX3tOX8Tngzg349q7t5xcfzpKGhOFHnjx+9qLTzW8wsmFTL2Gzk7Y2O/k9kCbtwUZbV+' \
                  b'Zvo8Md3PALrjoiqsKSR9ljpAJpwOsNtlfXfRvoNU8Arr/NsVo0ry5z4dZN5hoGqEzYDChBOo' \
                  b'KwS/vSq0XW3y5NAI/uN1cvLqzQur4MCpBGEEd1PQDfQ74HYR+LfeQOAOYAmgAmbly+dgfid5CHP' \
                  b'IKqC74L8RDyGPIYy7+QQjFWa7ICsQ8SpB/IfcJSDVMAJUwJkYDMNOEPIBxA/gnuMyYPijXAI3lMs' \
                  b'e7FGnIKsIuqrxgRSeXOoYZUCI8pIKW/OHA7kD2YYcpAKgM5ABXk4qSsdJaDOMCsgTIYAlL5TQFTy' \
                  b'UIZDmev0N/bnwqnylEBQS45UKnHx/lUlFvA3fo+jwR8ALb47/oNma38cuqiJ9AAAAAASUVORK5CYII='
    file_icon = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAABU0lEQV' \
                b'Q4y52TzStEURiHn/ecc6XG54JSdlMkNhYWsiILS0lsJaUsLW2Mv8CfIDtr2VtbY4GUEvmIZnKbZsY977Uwt2H' \
                b'cyW1+dTZvt6fn9557BGB+aaNQKBR2ifkbgWR+cX13ubO1svz++niVTA1ArDHDg91UahHFsMxbKWycYsjze4mu' \
                b'TsP64vT43v7hSf/A0FgdjQPQWAmco68nB+T+SFSqNUQgcIbN1bn8Z3RwvL22MAvcu8TACFgrpMVZ4aUYcn77BM' \
                b'DkxGgemAGOHIBXxRjBWZMKoCPA2h6qEUSRR2MF6GxUUMUaIUgBCNTnAcm3H2G5YQfgvccYIXAtDH7FoKq/AaqKl' \
                b'brBj2trFVXfBPAea4SOIIsBeN9kkCwxsNkAqRWy7+B7Z00G3xVc2wZeMSI4S7sVYkSk5Z/4PyBWROqvox3A28' \
                b'PN2cjUwinQC9QyckKALxj4kv2auK0xAAAAAElFTkSuQmCC'

    def add_files_in_folder(parent, dirname):
        files = os.listdir(dirname)
        for f in files:
            fullname = os.path.join(dirname, f)
            if os.path.isdir(fullname):
                treedata.Insert(parent, fullname, f, values=[], icon=folder_icon)
                add_files_in_folder(fullname, fullname)
            else:
                path, ext = os.path.splitext(fullname)
                if ext == '.pdf':
                    treedata.Insert(parent, fullname, f, values=[], icon=file_icon)

    add_files_in_folder('', dir_path)
    return treedata


def refresh_pdf_viewer(pdf_path):
    print(pdf_path)
    data = read_pdf(pdf_path)
    img = Image.open(io.BytesIO(data))
    image = img.resize((500, 700), PIL.Image.ANTIALIAS)
    output = io.BytesIO()
    image.save(output, format="png")
    ndata = output.getvalue()
    window['image_viewer'].update(data=ndata, size=(500, 700))


def refresh_folder_tree():
    global treedata
    treedata = create_folder_tree(default_dldir)
    window['_TREE_'].update(values=treedata)


def key_to_id(key):
    for k, v in window['_TREE_'].IdToKey.items():
        if v == key:
            return k
    return None


def check_expand_dirs():
    global treedata
    global open_dirs

    for key in treedata.tree_dict:
        node = treedata.tree_dict[key]
        if key_to_id(key):
            item = window['_TREE_'].Widget.item(key_to_id(key))
            if item['open']:
                open_dirs.append(key)


def open_expand_dirs():
    global treedata
    global open_dirs

    for key in treedata.tree_dict:
        if key in open_dirs:
            print(key)
            window['_TREE_'].Widget.item(key_to_id(key), open=True)


def delete_tree_node(window, key):
    global open_dirs
    global treedata

    open_dirs.clear()
    check_expand_dirs()

    if key == '':
        return
    node = treedata.tree_dict[key]
    parent_node = treedata.tree_dict[node.parent]
    parent_node.children.remove(node)
    window['_TREE_'].Update(values=treedata)
    open_expand_dirs()


def create_window():
    global treedata
    sg.theme('Default1')
    treedata = create_folder_tree(default_dldir)

    t1 = sg.Tab('Options', [
        [sg.Text('URL  '), sg.Input(key='URL_input')],
        [sg.Text('XPath'), sg.Input(default_text='/html/body', key='Xpath_input')],
        [sg.T('', font='any 1')],
        # [sg.Text("Download folder "), sg.Input(key='-IN1-'), sg.FolderBrowse()],
        [sg.T('', font='any 1')],
        [sg.Checkbox('Same domain only', default=True, key='samedomain_checkbox')],
        [sg.Checkbox('Check parent dirctory', default=True, key='parent_checkbox')],
        [sg.Checkbox('Use chrome profile', default=False, key='profile_checkbox')],
        [sg.T('', font='any 1')],
        [sg.Text('Depth'), sg.Combo(['1', '2', '3', '4', '5', '6', '7', '8', '9'],
                                    default_value='2', key='depth_combo')],
        [sg.T('', font='any 1')],
        [sg.Text('Store'), sg.Combo(['tree', 'sequential'], default_value='tree', key='store_combo')],
        [sg.T('', font='any 1')],
        [sg.T('', font='any 1')],
        [sg.Frame('Translate', [
            [sg.Checkbox('Google translate', default=False, key='gtranslate_checkbox')],
            [sg.Text('Src '), sg.Combo(cconde, default_value='en', key='tsrc_combo')],
            [sg.Text('Dist'),
             sg.Combo(cconde, default_value='ja', key='tdist_combo')],
        ])],
        [sg.T('', font='any 1')],
        [sg.T('', font='any 1')],
        [sg.Spin([i for i in range(1000, 1000000)],
                 initial_value=1000, key='recursion_spin'), sg.Text('Recursion limit')],
        [sg.T('', font='any 1')],
        [sg.T('', font='any 1')],
        [sg.T('', font='any 1')],
        [sg.T('', font='any 1')],
        [sg.Button('Start', size=(24, 2), key='_START_'), sg.Button('Stop', size=(24, 2), key='_STOP_')]
    ])
    t2 = sg.Tab('Log', [
        [sg.Multiline(size=(112, 45), font=('Consolas', 10), key='Output', disabled=True, )],
    ])
    t3 = sg.Tab('PDF Tree View', [
        [sg.Frame('', [
            [sg.Button('Refresh', size=(10, 1), key='_REFRESH_'), sg.Button('Delete', size=(10, 1), key='_DELETE_')],
            [sg.Tree(data=treedata, headings=[], auto_size_columns=True, num_rows=32, col0_width=30,
                     key='_TREE_', enable_events=True, show_expanded=False, )]]),
         sg.Image(data=None, key='image_viewer', size=(500, 700))
         ],
    ])
    layout = [
        [sg.TabGroup([[t1, t2, t3]])]
    ]
    return sg.Window("Web to PDF", layout)


def main(args):
    for root, dirs, files in os.walk("screenshot"):
        for file in files:
            os.remove(os.path.join(root, file))

    global window
    window = create_window()
    loop_check_msg(window)


if __name__ == '__main__':
    main(sys.argv[1:])
