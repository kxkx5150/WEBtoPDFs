import sys
import os.path
from selenium import webdriver
from selenium.webdriver.chrome import service as fs
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from logging import getLogger, StreamHandler, DEBUG
import time
import json
from urllib.parse import urlparse

options = webdriver.ChromeOptions()
options.add_argument('--disable-gpu')
options.add_argument('--disable-extensions')
options.add_argument('--proxy-server="direct://"')
options.add_argument('--proxy-bypass-list=*')
options.add_argument('--start-maximized')
options.add_argument('--start-maximized')
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


def save_pdf(driver, wait):
    wait.until(EC.presence_of_all_elements_located)
    driver.execute_script('window.print()')
    time.sleep(10)


def check_page(driver, page_url, samedomain, parentdir):
    crnt_url = urlparse(page_url)
    print(crnt_url.scheme)
    print(crnt_url.netloc)
    print(crnt_url.path)
    print(crnt_url.query)
    print('---')

    prntelem = driver.find_element(by=By.XPATH, value='//*[@id="bodyContent"]/div[4]/table/tbody/tr/td[1]/div[1]/ul[1]')
    elems = prntelem.find_elements(By.XPATH, 'descendant::*[@href]')

    if prntelem:
        for elem in elems:
            lnk_url = urlparse(elem.get_attribute("href"))
            if samedomain and crnt_url.netloc == lnk_url.netloc:
                print(lnk_url.netloc)





def start(driver, wait, page_url, samedomain, parentdir):
    driver.implicitly_wait(5)
    driver.get(page_url)
    # save_pdf(driver, wait)
    check_page(driver, page_url, samedomain, parentdir)


def init(top_url, samedomain, parentdir):
    chrome_servie = fs.Service(executable_path="chromedriver.exe")
    driver = webdriver.Chrome(service=chrome_servie, options=options)
    wait = WebDriverWait(driver, 5)
    start(driver, wait, top_url, samedomain, parentdir)
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

    samedomain = input('same domain only ? (y or n) : ')
    if samedomain == 'n' :
        samedomain = False
    else:
        samedomain = True

    parentdir = input('parent dirctory ? (y or n) : ')
    if parentdir == 'y' :
        parentdir = True
    else:
        parentdir = False

    init(top_url, samedomain, parentdir)


if __name__ == '__main__':
    main(sys.argv[1:])

