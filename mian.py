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


def check_page(driver, page_url, samedomain, prntcheck, xpath, prntnode):
    prntelem = driver.find_element(by=By.XPATH, value=xpath)
    elems = prntelem.find_elements(By.XPATH, 'descendant::*[@href]')
    linknodes = LinkNodes(page_url, prntnode, samedomain, prntcheck)

    if prntelem:
        for elem in elems:
            href = elem.get_attribute("href")
            lnknod = LinkNode(href, prntnode)
            linknodes.check_append(lnknod)
            
    prntnode.apped_link_nodes(linknodes)
    return prntnode


def start(driver, wait, page_url, samedomain, prntcheck, xpath, prntnode):
    driver.implicitly_wait(5)
    driver.get(page_url)
    # save_pdf(driver, wait, prntnode)
    lnknod = check_page(driver, page_url, samedomain, prntcheck, xpath, prntnode)
    print(lnknod)


def init(top_url, samedomain, prntcheck, xpath):
    chrome_servie = fs.Service(executable_path="chromedriver.exe")
    driver = webdriver.Chrome(service=chrome_servie, options=options)
    wait = WebDriverWait(driver, 5)
    toplnk = LinkNode(top_url, None)
    start(driver, wait, top_url, samedomain, prntcheck, xpath, toplnk)
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

    init(top_url, samedomain, prntcheck, xpath)


if __name__ == '__main__':
    main(sys.argv[1:])
