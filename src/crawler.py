# -*- coding: utf-8 -*-
import requests
import string
import time
import urllib.parse
import csv
import os
from bs4 import BeautifulSoup

def parse_band_list_html(html):
    soup = BeautifulSoup(html,"html.parser")
    ret = {}
    for div in soup.find_all("div", {"class": "artists"}):
        for link in div.find_all("a"):
            ret[link["href"]] = link.text
    return ret

def parse_album_list_html(html):
    soup = BeautifulSoup(html,"html.parser")
    ret = {}
    for div in soup.find_all("div", {"class": "album"}):
        name = div.find("h2").text
        link = div.find("a")["href"]
        ret[link] = name
    return ret

def get_band_list(letter):
    url = "http://www.darklyrics.com/{letter}.html".format(letter=letter)
    try:
        r = requests.get(url)
    except requests.exceptions.ConnectionError as e:
        print(e)
        return -1, None
    if r.status_code == 200:
        return r.status_code, parse_band_list_html(r.text)
    else:
        return r.status_code, None

def get_album_list(band_url):
    base_url = "http://www.darklyrics.com"
    url = urllib.parse.urljoin(base_url,band_url)
    print(url)
    try:
        r = requests.get(url)
    except requests.exceptions.ConnectionError as e:
        print(e)
        return -1, None
    if r.status_code == 200:
        return r.status_code, parse_album_list_html(r.text)
    else:
        return r.status_code, None

def save_band_list():
    with open("../data/bands.csv", "w", encoding="utf-8") as f:
        csv_writer = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator="\n")
        for letter in list(string.ascii_lowercase):
            rc, data = get_band_list(letter)
            while rc != 200:
                print("RC = ", rc)
                print("Error on request. Waiting 60 seconds.")
                time.sleep(60)
                rc, data = get_band_list(letter)
            print(letter, len(data))
            for url, name in data.items():
                csv_writer.writerow((url,name))

def append_album_list(csv_writer, band_url):
    try:
        rc, albuns = get_album_list(band_url)
        while rc != 200:
            print("RC = ", rc)
            print("Error on request. Waiting 60 seconds.")
            time.sleep(60)
            rc, albuns = get_album_list("a/angra.html")
        csv_writer.writerows(map(lambda x: (band_url,) + x, albuns.items()))
    except Exception as e:
        print("ERROR!")
        print("BAND URL =", band_url)
        print("ERROR MESSAGE = ", e)

if __name__ == "__main__":
    save_band_list()
    with open("../data/albuns.csv", "w", encoding="utf-8") as f_o:
        csv_writer = csv.writer(f_o, quoting=csv.QUOTE_ALL)
        with open("../data/bands.csv", "r", encoding="utf-8") as f_i:
            csv_reader = csv.reader(f_i, quoting=csv.QUOTE_ALL, lineterminator="\n")
            for band_url, band in csv_reader:
                print(band_url, band)
                append_album_list(csv_writer, band_url)


