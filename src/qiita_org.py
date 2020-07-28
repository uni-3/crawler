# config: utf8
import pandas as pd

from requests_html import HTML
from requests_html import HTMLSession
import json
import time
import re


base_url = "https://qiita.com/organizations"
orgs_selector = "body > div.allWrapper > div.p-organizations > div.px-2.px-1\@s.pt-4.pt-1\@s > div > div.p-organizations_main > div > div:nth-of-type(n+2)" # headerは覗く
logo_selector = "body > div.allWrapper > div.p-organizations > div.px-2.px-1\@s.pt-4.pt-1\@s > div > div.p-organizations_main > div > div:nth-child(2) > div.ol-Item_image.mr-1 > a > img"
logo_selector = "div.ol-Item_image.mr-1 > a > img"
org_name_selector = "div.ol-Item_content.mr-1 > strong > a"
pager_selector = "body > div.allWrapper > div.p-organizations > div.px-2.px-1\@s.pt-4.pt-1\@s > div > div.p-organizations_main > div > div.ol-ItemList_pager > ul > li.st-Pager_next > a"


# https://stackoverflow.com/questions/45846765/efficient-way-to-unnest-explode-multiple-list-columns-in-a-pandas-dataframe


def get_org_detail(link):
    d = {}

    session = HTMLSession()
    r = session.get(link)

    # 記事数とgood数
    counter_selector = "body > div.allWrapper > div.p-organization_wrapper > div.p-organization_container > div > div.op-SideCard.op-SideCard-narrow > div.op-About > div.op-Counter > dl"
    for cell in r.html.find(counter_selector):

        c = cell.find("dd", first=True).text
        n = cell.find("dt", first=True).text

        if n == "Posts":
            d["n_posts"] = c
        elif n == "LGTMs":
            d["n_goods"] = c

    # linkとaddr
    addr_selector = "body > div.allWrapper > div.p-organization_wrapper > div.p-organization_container > div > div.op-SideCard.op-SideCard-narrow > div.pl-3.pr-3 > section:nth-child(1)"
    addr = r.html.find(addr_selector, first=True)
    #d["org_email"] = addr.find("h2 > span", itemprop="email", first=True).text

    d["org_url"] = ""
    org_url = addr.find("h2 > a[itemprop=url]", first=True)
    if org_url is not None:
        d["org_url"] =  org_url.attrs["href"]

    # emailがなかったら
    d["org_email"] = ""
    org_email = addr.find("h2 > span[itemprop=email]", first=True)
    if org_email is not None:
        d["org_email"] = org_email.text

    d["org_addr"] = ""
    org_addr = addr.find("h2[itemprop=address]", first=True)
    if org_addr is not None:
        d["org_addr"] = org_addr.text


    # description
    desc_selector = "body > div.allWrapper > div.p-organization_wrapper > div.p-organization_container > div > div.op-SideCard.op-SideCard-narrow > div.op-About > div.op-About_body > p"
    desc = r.html.find(desc_selector, first=True)
    d["org_description"] = ""
    if desc is not None:
        d["org_description"] = desc.text

    # content
    content_selector = "body > div.allWrapper > div.p-organization_wrapper > div.p-organization_detail > div:nth-child(1) > div"
    content = r.html.find(content_selector, first=True)
    d["org_content"] = ""
    if content is not None:
        d["org_content"] = content.text

    # n_member
    m_selector = "body > div.allWrapper > div.p-organization_wrapper > div.p-organization_container > div > div:nth-child(2) > section > h2 > span > span > span:nth-child(2)"
    n_member = r.html.find(m_selector, first=True)
    d["n_member"] = ""
    if n_member is not None:
        d["n_member"] = re.sub(r"\D", "", n_member.text)

    # member link list
    member_list_selector = "body > div.allWrapper > div.p-organization_wrapper > div.p-organization_container > div > div:nth-child(2) > section > div > ul"
    member_list = r.html.find(member_list_selector, first=True)
    d["member_url_list"] = list(member_list.absolute_links)


    # tag list
    tag_list_selector = "body > div.allWrapper > div.p-organization_wrapper > div.p-organization_detail > div:nth-child(3) > div.od-Content_section.ot-TagList > div"
    tag_list = r.html.find(tag_list_selector)
    tags = []
    #print("tag_list", tag_list)
    for tag in tag_list:
        dd = {}

        dd['name'] = tag.find("div > a > span", first=True).text
        dd['icon'] = tag.find("div > a > img", first=True).attrs["src"]


        for t in tag.find("div"):
            c = t.find(".ot-TagItem_countValue", first=True).text
            n = t.find(".ot-TagItem_countLabel", first=True).text

            if n == "Posts":
                dd["post"] = c
            elif n == "LGTMs":
                dd["good"] = c

        tags.append(dd)

    d["popular_tags"] = tags

    return d


#def get_orgs_page(orgs_html):

def save_json(res, filename):
    with open(filename, "w") as f:
        json.dump(res, f)


def save_as_csv(filename="qiita_org.json"):
    with open(filename) as f:
        json_dict = json.load(f)

    df = pd.io.json.json_normalize(data=json_dict)

    df_member = pd.DataFrame()
    df_popular_tags = pd.DataFrame()

    # explode and merge for dataframe
    # @see https://www.geeksforgeeks.org/pandas-parsing-json-dataset/
    member_key = "member_url_list"
    popular_tags_key = "popular_tags"
    "name" "icon" "post" "good"
    for j in json_dict:
        if not (member_key in j.keys()) or not (popular_tags_key in j.keys()):
            continue

        df_member = df_member.append(
            pd.io.json.json_normalize(
                data=j, record_path=member_key, meta=["name"]
            ),
            sort=False,
        )

        df_popular_tags = df_popular_tags.append(
            pd.io.json.json_normalize(
                data=j, record_path=popular_tags_key,
                meta=["name"], record_prefix='tag_'
            ),
            sort=False,
        )


    #df = df.merge(df_member, on="name")
    df = df.merge(df_popular_tags, on="name") #, suffixes=["_tag", "_stat"])

    #df["title_tag"] = df["title_tag"].str.rstrip()

    #del df[0]
    del df["popular_tags"]
    #del df["d_name"]

    df.to_csv("qiita_org.csv", index=False)


def crawl():
    org_list = []
    session = HTMLSession()
    r = session.get(base_url)

    orgs_html = r.html.find(orgs_selector)

    # TODO ページャ対応
    # 組織一覧がいなくなる=ページが0になるまで
    i = 1
    while orgs_html[0].find(org_name_selector, first=True) is not None:
        url = base_url + "?page=" + str(i)
        i = i + 1
        print('crawl ', url)

        session = HTMLSession()
        r = session.get(url)

        orgs_html = r.html.find(orgs_selector)

        # get orgs detail
        for org in orgs_html:
            d = {}

            org_name_a = org.find(org_name_selector, first=True)
            org_detail_link = ""
            d["detail_page_url"] = ""
            if org_name_a is not None:
                org_detail_link = list(org_name_a.absolute_links)[0]
                d["detail_page_url"] = org_detail_link


            logo_url = org.find(logo_selector, first=True)
            d["logo_url"] = ""
            if logo_url is not None:
                d["logo_url"] = logo_url.attrs["src"]

            d["name"] = ""
            if org_name_a is not None:
                d["name"] = org_name_a.text
            print(f"scrape...{d['name']}")
            print(org_detail_link)

            d_detail = {}
            if org_detail_link is not "":
                d_detail = get_org_detail(org_detail_link)

            d.update(d_detail)

            time.sleep(1)

            org_list.append(d)
            #break

        #print(org_list)

    print('len org', len(org_list))
    save_json(org_list, "qiita_org.json")

    # r.html.absolute_links


if __name__ == "__main__":
    #crawl()
    save_as_csv(filename="qiita_org.json")
