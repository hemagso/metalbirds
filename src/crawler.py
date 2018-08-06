# -*- coding: utf-8 -*-
import os
import requests
import pandas as pd
import time
import sys
import signal
from datetime import datetime
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
            return get_songs_page(session, link, retries=retries+1, max_retries=max_retries)


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


def parse_song_lyrics_html(html):
    soup = BeautifulSoup(html,"html.parser")
    div = soup.find("div", {"itemprop" : "lyrics"})
    return div.text


def get_song_lyrics(session, link, retries=0, max_retries=10):
    url = requests.compat.urljoin("https://www.metalkingdom.net/", link)
    try:
        r = session.get(url)
        if r.status_code == 200:
            return r.status_code, parse_song_lyrics_html(r.text)
        else:
            return r.status_code, None
    except requests.exceptions.ConnectionError as e:
        if retries > max_retries:
            print("Maximum number of retries achieved. Skipping record.")
            return -1, None
        else:
            print("Connection Error Detected. Waiting 60 seconds and trying again ({retries})".format(retries=retries))
            time.sleep(60)
            return get_song_lyrics(session, link, retries=retries+1, max_retries=max_retries)


def save_song_lyrics(path, df_songs, replace=False):
    if replace or not os.path.exists(path):
        session = requests.Session()
        df = pd.DataFrame.copy(df_songs)
        i = 0
        n = df.shape[0]

        def wrapper(x):
            nonlocal i
            if i % 500 == 0:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print("[{ts}] {i} / {n}".format(ts=ts, i=i, n=n))
            i = i + 1
            rc, lyrics = get_song_lyrics(session, x.SongURL)
            if rc == 200:
                return lyrics
            else:
                return "RC !- 200"
        df["lyrics"] = df.apply(wrapper, axis=1)
        df.to_csv(path)
        return True
    else:
        print("Lyrics file already existed. Use replace=True to force update")
        return False


def parse_band_genre_html(html):
    soup = BeautifulSoup(html,"html.parser")
    span = soup.find("span", {"itemprop" : "genre"})
    return span.text


def get_band_genre(session, band_url):
    base_url = "http://www.metalkingdom.net"
    url = requests.compat.urljoin(base_url,band_url)
    try:
        r = session.get(url)
    except requests.exceptions.ConnectionError as e:
        print(e)
        return -1, None
    if r.status_code == 200:
        return r.status_code, parse_band_genre_html(r.text)
    else:
        return r.status_code, None


def save_band_genre(path, df_bands, replace=False):
    if replace or not os.path.exists(path):
        session = requests.Session()
        df = pd.DataFrame.copy(df_bands)
        i = 0
        n = df.shape[0]

        def wrapper(x):
            nonlocal i
            if i % 500 == 0:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print("[{ts}] {i} / {n}".format(ts=ts, i=i, n=n))
            i = i + 1
            rc, genre = get_band_genre(session, x.BandURL)
            if rc == 200:
                return genre
            else:
                return "RC !- 200"

        df["genre"] = df.apply(wrapper, axis=1)
        df.to_csv(path)
        return True
    else:
        print("Genre file already existed. Use replace=True to force update")
        return False

def fix_band_genre():
    df_genre = pd.read_csv("../data/genre.csv")
    session = requests.Session()
    def wrapper(x):
        if x.genre == "RC !- 200":
            rc, genre = get_band_genre(session, x.BandURL)
            if rc == 200:
                return genre
            else:
                return "RC !- 200"
        else:
            return x.genre

    df_genre["genre"] = df_genre.apply(wrapper, axis=1)
    df_genre.to_csv("../data/genre_fixed.csv")

if __name__ == "__main__":
    #save_band_list("../data/bands.csv", replace=False)
    #df_bands = pd.read_csv("../data/bands.csv")
    #save_songs_list("../data/songs.csv", df_bands, replace=False)
    #df_songs = pd.read_csv("../data/songs.csv")
    #save_song_lyrics("../data/lyrics_01.csv", df_songs.iloc[0:50000], replace=False)
    #save_song_lyrics("../data/lyrics_02.csv", df_songs.iloc[50000:100000], replace=False)
    #save_song_lyrics("../data/lyrics_03.csv", df_songs.iloc[100000:], replace=False)
    #save_band_genre("../data/genre.csv", df_bands, replace=False)
    #fix_band_genre()
    df_1 = pd.read_csv("../data/lyrics_01.csv")
    df_2 = pd.read_csv("../data/lyrics_02.csv")
    df_3 = pd.read_csv("../data/lyrics_03.csv")
    df = pd.concat([df_1, df_2, df_3]).drop(columns="Unnamed: 0")
    df.to_csv("../data/lyrics.csv")

    #df_genre = pd.read_csv("../data/genre.csv").drop(columns=["Unnamed: 0", "Unnamed: 0.1"])
    #df_genre.to_csv("../data/genre_fix.csv")
    #print(df_genre.columns.values)

