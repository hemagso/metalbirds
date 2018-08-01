# -*- coding: utf-8 -*-
import os
import requests
import pandas as pd
import time
from bs4 import BeautifulSoup


def parse_band_list_html(html):
    soup = BeautifulSoup(html,"html.parser")
    ret = {}
    for tr in soup.find_all("tr", {"class": "top-line"}):
        for link in tr.find_all("a"):
            ret[link["href"]] = link.text[:-7]
    return ret


def get_band_page(page):
    url = "https://www.metalkingdom.net/lyrics/list.php"
    r = requests.get(url,params={"start" : page})
    if r.status_code == 200:
        return r.status_code, parse_band_list_html(r.text)
    else:
        return r.status_code, None


def get_band_list(limit=100):
    ret = {}
    for i in range(1, limit+1):
        rc, page = get_band_page(i)
        print("Page {i} [{rc}] ({n})".format(i=i,rc=rc, n=len(page)))
        if rc == 200:
            if page:
                ret.update(page)
            else:
                break
    df = pd.DataFrame.from_dict(ret,orient="index",columns=["BandName"])
    df.index.name = "BandURL"
    return df


def save_band_list(path, limit=100,replace=False):
    if replace or not os.path.exists(path):
        df = get_band_list(limit=limit)
        df.to_csv(path)
        return True
    else:
        print("Bands file already existed. Use replace=True to force update")
        return False


def parse_song_list_html(band_key, html):
    soup = BeautifulSoup(html,"html.parser")
    ret = {}
    table = soup.find(id="bly-song-tb")
    for link in table.find_all("a"):
        ret[link["href"]] = (link.text[:-7], band_key)
    return ret


def get_songs_page(session, link, retries=0, max_retries=10):
    url = requests.compat.urljoin("https://www.metalkingdom.net/", link)
    try:
        r = session.get(url)
        if r.status_code == 200:
            return r.status_code, parse_song_list_html(link, r.text)
        else:
            return r.status_code, None
    except requests.exceptions.ConnectionError as e:
        if retries > max_retries:
            print("Maximum number of retries achieved. Skipping record.")
            return -1, None
        else:
            print("Connection Error Detected. Waiting 60 seconds and trying again ({retries})".format(retries=retries))
            time.sleep(60)
            return get_songs_page(link, retries=retries+1, max_retries=max_retries)


def get_songs_list(df_bands):
    ret = {}
    session = requests.Session()
    for idx, row in df_bands.iterrows():
        rc, page = get_songs_page(session,row.BandURL)
        print("Band {idx} [{rc}] ({n})".format(idx=idx,rc=rc, n=len(page)))
        if rc == 200:
            ret.update(page)
        else:
            print("Error requesting URL =",row.BandURL)
        #time.sleep(0.1)
    df = pd.DataFrame.from_dict(ret,orient="index",columns=["SongName", "BandURL"])
    df.index.name = "SongURL"
    return df


def save_songs_list(path, df_bands, replace=False):
    if replace or not os.path.exists(path):
        df = get_songs_list(df_bands)
        df.to_csv(path)
        return True
    else:
        print("Songs file already existed. Use replace=True to force update")
        return False

if __name__ == "__main__":
    save_band_list("../data/bands.csv", replace=False)
    df_bands = pd.read_csv("../data/bands.csv")
    save_songs_list("../data/songs.csv", df_bands, replace=True)
