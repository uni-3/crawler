from bs4 import BeautifulSoup
import requests
import pandas as pd
import numpy as np

from collections import defaultdict
import re
import json
import time

BASE_URL = "https://www.connosr.com"
D_URL = "https://www.connosr.com/whisky-brands-distilleries"

# css selector
brands_selector = "#wrapper > div.tab-menu.collapse-menu.collapse-grey > div > nav > ul"
distilleries_selector = (
    "#wrapper > section.index-section.margin-top-extra.margin-bottom-extra > section"
)


def get_links(soup, selector=brands_selector):
    """
    指定したselectの下にあるliのリンクを取ってくる
    """

    links = []
    ul = soup.select(selector)
    # print(ul)
    for u in ul:
        for li in u:
            # print(li)
            a_tag = li.find("a")
            # print(a_tag.text)

            links.append({"name": a_tag.text, "link": BASE_URL + a_tag.get("href")})

    return links


def get_distillery(soup):
    from collections import defaultdict

    details = defaultdict()
    name_selector = "#wrapper > section.header-brand > article > h1"

    if not soup.select(name_selector):
        return details

    name = soup.select(name_selector)[0]
    # print('name', name)

    # get .text ex.) Islay Whisky Scotch Whisky
    profile_selector = "#wrapper > section.header-brand > article > div > p.strap"
    profile = soup.select(profile_selector)
    # print('profile div', profile)
    for p in profile:
        # print('profile', p.text)
        # extact from '#1 in Islay Whisky and #1 in Scotch Whisky'
        profile = " ".join(p.text.split(" ")[3:5])

    # score etc...
    # class stat
    # class title
    stats_selector = "#wrapper > section.stats > div > ul"
    stats_ul = soup.select(stats_selector)

    stats = []
    for s in stats_ul[0]:
        # print('s', s)
        title = s.find(class_="title").text
        stat = s.find(class_="stat").text
        stats.append({"title": title, "stat": stat})

    # tag ex peaty 10
    tags_selector = "#wrapper > section:nth-child(13) > div > article > ul"
    tags_ul = soup.select(tags_selector)
    # print('tags_ul', tags_ul)

    tags = []
    if tags_ul:
        for t in tags_ul[0]:
            # print('t', t)
            title, count = re.findall(r"(\d+|\D+)", t.text)
            # title, count = t.text.split(' ')
            tags.append({"title": title, "count": count})

    details = {
        "distillery_name": name.text,
        "profile": profile,
        "stats": stats,
        "tags": tags,
    }

    return details


def crawl_data(filename="whiskies.json"):
    results = []
    brands_html = BeautifulSoup(requests.get(D_URL).text, "lxml")

    brands = get_links(brands_html, selector=brands_selector)
    # print(brands)

    for b in brands:
        if b.get("link") == "https://www.connosr.com/whisky-brands-distilleries":
            continue
        distilleries_html = BeautifulSoup(requests.get(b.get("link")).text, "lxml")

        distilleries = get_links(distilleries_html, selector=distilleries_selector)
        # print(distilleries)

        time.sleep(1)

        for d in distilleries:
            distillery_html = BeautifulSoup(requests.get(d.get("link")).text, "lxml")

            details = get_distillery(distillery_html)

            time.sleep(1)

            # add meta data
            # for detail in details:
            details["brand_name"] = b.get("name")
            details["list_link"] = b.get("link")
            details["d_name"] = d.get("name")
            details["detail_link"] = d.get("link")

            print("collected ", d.get("name"), details)
            results.append(details.copy())

    # to JSON
    with open(filename, "w") as f:
        json.dump(results, f)


def save_as_csv(filename="whiskies.json"):
    with open(filename) as f:
        json_dict = json.load(f)

    df = pd.io.json.json_normalize(data=json_dict)

    df_tags = pd.DataFrame()
    df_stats = pd.DataFrame()

    # explode and merge for dataframe
    # @see https://www.geeksforgeeks.org/pandas-parsing-json-dataset/
    for j in json_dict:
        if not ("tags" in j.keys()) or not ("stats" in j.keys()):
            continue

        df_tags = df_tags.append(
            pd.io.json.json_normalize(
                data=j, record_path="tags", meta=["distillery_name"]
            ),
            sort=False,
        )

        df_stats = df_stats.append(
            pd.io.json.json_normalize(
                data=j, record_path="stats", meta=["distillery_name"]
            ),
            sort=False,
        )

    df = df.merge(df_tags, on="distillery_name")
    df = df.merge(df_stats, on="distillery_name", suffixes=["_tag", "_stat"])

    df["title_tag"] = df["title_tag"].str.rstrip()

    del df["tags"]
    del df["stats"]
    del df["d_name"]

    df.to_csv("whiskies.csv", index=False)


if __name__ == "__main__":
    filename = "whiskies.json"
    crawl_data(filename)
    save_as_csv(filename)
