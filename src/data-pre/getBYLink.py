import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
import argparse

parser = argparse.ArgumentParser(description='读取搜索内容')
parser.add_argument('-q', '--query', required=True, help='搜索内容')
args = parser.parse_args()
q = args.query
if len(q) == 0:
    q = "Privacy+Preserving+Computing"

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
service = Service('/usr/local/bin/chromedriver')
driver = webdriver.Chrome(service=service, options=chrome_options)
with open('output.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Page", "Result", "Title", "Link", "Abstract", "Keywords", "Authors"])
    try:
        base_url = "https://scholar.google.com.hk/scholar?start={}&q={}&hl=zh-CN&as_sdt=0,5"
        for i in range(50):
            driver.get(base_url.format(i*10, q))
            results = driver.find_elements(By.CSS_SELECTOR, "div.gs_ri")
            print("Search results loaded.")
            for index, result in enumerate(results, start=1):
                try:
                    title = result.find_element(By.CSS_SELECTOR, "h3.gs_rt a").text
                except NoSuchElementException:
                    title = ""
                try:
                    link = result.find_element(By.CSS_SELECTOR, "h3.gs_rt a").get_attribute('href')
                except NoSuchElementException:
                    link = ""
                try:
                    abstract = result.find_element(By.CSS_SELECTOR, "div.gs_rs").text
                except NoSuchElementException:
                    abstract = ""
                try:
                    keywords = result.find_element(By.CSS_SELECTOR, "div.gs_a").text.split(" - ")[-1]
                except NoSuchElementException:
                    keywords = ""
                try:
                    authors = result.find_element(By.CSS_SELECTOR, "div.gs_a").text.split(" - ")[0]
                except NoSuchElementException:
                    authors = ""
                writer.writerow([i+1, index, title, link, abstract, keywords, authors])
    finally:
        driver.quit()