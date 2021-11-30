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
    "printing.print_preview_sticky_settings.appState":
        json.dumps(appState),
    "download.default_directory": '~/Downloads'
})
options.add_argument('--kiosk-printing')

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


def save_pdf(driver, wait, prntnode):
    wait.until(EC.presence_of_all_elements_located)
    driver.execute_script('window.print()')
    time.sleep(10)


def check_page(driver, page_url, linknodes, app_options):
    prntnode = linknodes.get_current_node()
    prntelem = driver.find_element(by=By.XPATH, value=app_options['xpath'])
    elems = prntelem.find_elements(By.XPATH, 'descendant::*[@href]')
    child_linknodes = LinkNodes(page_url, prntnode, app_options)

    if prntelem:
        for elem in elems:
            href = elem.get_attribute("href")
            lnknod = LinkNode(href, prntnode)
            child_linknodes.check_append(lnknod)
            lnknod.set_current_linknodes(child_linknodes)

    prntnode.link_check = True
    prntnode.append_link_nodes(child_linknodes)
    linknodes.inc_check_index()


def start(driver, wait, linknodes, page_url, crnt_depth, app_options):
    driver.implicitly_wait(5)
    driver.get(page_url)
    # save_pdf(driver, wait, prntnode)
    if crnt_depth < app_options['depth']:
        check_page(driver, page_url, linknodes, app_options)

    crnt_depth += 1
    pass


def init(top_url, app_options):
    chrome_servie = fs.Service(executable_path="chromedriver.exe")
    driver = webdriver.Chrome(service=chrome_servie, options=options)
    wait = WebDriverWait(driver, 5)

    toplnk = LinkNode(top_url, None)
    linknodes = LinkNodes(top_url, None, app_options)
    linknodes.append_node(toplnk)
    toplnk.set_current_linknodes(linknodes)

    start(driver, wait, linknodes, top_url, 1, app_options)
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

    prntcheck = input('parent dirctory ? (y or n)Default y: ')
    if prntcheck == 'n':
        prntcheck = False
    else:
        prntcheck = True

    xpath = input('links in target element ? (XPATH)Default /html/body : ')
    if not xpath:
        xpath = '/html/body'
    # '//*[@id="bodyContent"]/div[4]/table/tbody/tr/td[1]/div[1]/ul[1]'

    app_options = {
        'samedomain': samedomain,
        'prntcheck': prntcheck,
        'xpath': xpath,
        'depth': 2
    }

    init(top_url, app_options)


if __name__ == '__main__':
    main(sys.argv[1:])
