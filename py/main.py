import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

import scraperutils as gsf
from selenium_stealth import stealth
from bs4 import BeautifulSoup as bs
from selenium import webdriver
import requests as requests
import datetime as dt
import pandas as pd
import time
import json
import re

SIGNIN_URL = "https://www.goodreads.com/ap/signin?language=en_US&openid.assoc_handle=amzn_goodreads_web_na&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.mode=checkid_setup&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.goodreads.com%2Fap-handler%2Fsign-in&siteState=eyJyZXR1cm5fdXJsIjoiaHR0cHM6Ly93d3cuZ29vZHJlYWRzLmNvbS8ifQ%3D%3D"
URL_TEMPLATE = "https://www.goodreads.com/review/list/8683189-ne?page=1&shelf=to-read"
NUM_BOOKS_PER_PAGE = 20
print("before driver set up")

service = Service()
options = webdriver.ChromeOptions()
web_driver = webdriver.Chrome(service=service, options=options)
print("after driver set up")

def signin_to_goodreads(driver: webdriver.Chrome):
    try:
        # Open the login page
        driver.get(SIGNIN_URL)

        # Find the email input field by ID and input your email
        email_input = driver.find_element(By.ID, "ap_email")
        email = os.getenv("USERNAME")
        email_input.send_keys(email)

        # Find the password input field by ID and input your password
        password_input = driver.find_element(By.ID, "ap_password")
        password = os.getenv("PASSWORD")
        password_input.send_keys(password)

        # Find the login button and submit the form
        login_button = driver.find_element(By.ID, "signInSubmit")
        login_button.click()

        # Wait for the login process to complete
        time.sleep(5)  # Adjust this depending on your site's response time
    except:
        print("login failed")


def scrape_tbr(url_temp:str, driver: webdriver.Chrome):
    """This functions scrapes through a good reads book list and writes to json file sample_data with the
    list of books released in the past 30 days. Book data contains author, title, cover url, book url and
    the publication date of the chosen edition"""

    # initialise master lists and get number of pages of tbr
    master_dict = {"Title": [], "Author": [], "Date": [], "Link": [], "Cover": []}
    print(URL_TEMPLATE)
    driver.get(URL_TEMPLATE)
    soup_1 = bs(driver.page_source, 'html.parser')
    num_tbr_pages = gsf.get_num_pages(NUM_BOOKS_PER_PAGE, soup_1)

    # add data to master lists
    for count, column in enumerate(master_dict):
        master_dict[column].extend(gsf.get_all_info(soup_1)[count])

    # loop through each page of tbr list for book data
    for i in range(2, num_tbr_pages+1):

        # update the url with new page number and get soup
        url = re.sub(r"page=[0-9]+", f"page={i}", url_temp)
        driver.get(url)
        html_soup = bs(driver.page_source, 'html.parser')
        print(i, end=", ")

        # add data to master lists
        for count, column in enumerate(master_dict):
            master_dict[column].extend(gsf.get_all_info(html_soup)[count])

    # turn master list into a pandas dataframe and convert date to datetime
    books_info = pd.DataFrame.from_dict(master_dict)
    books_info.loc[:, "Date"] = pd.to_datetime(books_info.loc[:, "Date"])
    books_info = books_info.sort_values(by=["Date"], ignore_index=True)

    # create dataframes for books released in the past month and in the upcoming week
    today = pd.to_datetime([dt.datetime.now().date()])
    day_30 = pd.to_datetime(today - dt.timedelta(days=30))
    day_7 = pd.to_datetime(today + dt.timedelta(days=7))
    books_month = books_info.loc[(books_info["Date"] >= day_30[0]) & (books_info["Date"] <= today[0])].reset_index(drop=True)
    books_week = books_info.loc[(books_info["Date"] <= day_7[0]) & (books_info["Date"] >= today[0])].reset_index(drop=True)

    books_dfs = {"full_tbr": books_info, "tbr_past_month": books_month, "tbr_coming_week": books_week}

    # convert date column in dataframes to string; convert dataframes to json and write to file
    for title, df in books_dfs.items():
        df["Date"] = df["Date"].dt.strftime("%b %d, %Y")
        df.to_json(f"../data/{title}.json", orient="records")

    driver.quit()

    return books_info, books_month, books_week

if __name__ == "__main__":
    signin_to_goodreads(web_driver)
    scrape_tbr(URL_TEMPLATE, web_driver)
