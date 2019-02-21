# coding: UTF-8
import requests
from bs4 import BeautifulSoup
import re # 正規表現用
from time import sleep      # 待ち時間用
from pprint import pprint  # 改行付き配列出力
import csv

SCRAPING_INTERVAL_TIME = 5.5

ranking_category_total = (
    "http://www.dlsite.com/maniax/ranking/day",
    # "http://www.dlsite.com/maniax/ranking/week",
    # "http://www.dlsite.com/maniax/ranking/month",
)

# ページネイションを含め、探査対象となるURL群を取得し配列に格納、返却する。
def getSearchTargetURLs(baseURLs) :

    for basePage in baseURLs :
        tgtpage = requests.get(basePage)
        pageUrls = []

        soup = BeautifulSoup(tgtpage.content, "html.parser")

        # ページネイションURLを取得
        pagenations = soup.select("li.ranking_pagination_item")

        # ページネイションが存在しない場合は単一ページだけなので入力URLのみリストに入れ続行
        if len(pagenations) == 0 :
            pageUrls.append(basePage)
            continue

        for pagina in pagenations :
            nexturl = pagina.find('a', href=True)
            pageUrls.append(nexturl['href'])

        # 重複要素を削除（順番を保持しない）
        pageUrls = list(set(pageUrls))

    pprint(pageUrls)

    return pageUrls

# 対象のプロダクトページが持つタグをすべて取得。タイトルと合わせて返す。
def getAttributeTags(tgturl) :
    tgtpage = requests.get(tgturl)

    sp = BeautifulSoup(tgtpage.content, "html.parser")

#    pageTitle = sp("h1")
    pageTitle = sp.select("h1")[0].text.strip()

    elems = sp.find_all(href=re.compile("work.genre"))

    tags = []

    for e in elems:
        tags.append(e.getText())

    print(pageTitle, end=" ")
    print(tags)
    return pageTitle, tags

# メイン処理スタート

# file open
f = open("RankingList.csv", "w")
writer = csv.writer(f, lineterminator="\n")
header = ["Title", "Tags"]
writer.writerow(header)

att_dict = {}

targetURLs = getSearchTargetURLs(ranking_category_total)

for url in targetURLs:

    # 対象URL : DLサイトランキング
    r = requests.get(url)

    # 第一引数＝解析対象　第二引数＝パーサー(何を元に解析するか：この場合はHTML)
    soup = BeautifulSoup(r.content, "html.parser")

    idx = 0
    # ランキングの順に従ってプロダクト名を取得する
    for rank in soup.select("dt.work_name"):

        idx+=1

        # タグ込文字列から個別ページへのURLを抽出（ひとつだけなのでfind_allでなくfind）
        tgturl = rank.find('a', href=True)

        # rankにはタグ等の情報も含まれているため、タイトルだけ抽出する
        # product_title = rank.getText()
        # product_title = product_title.strip()
        # print(str(idx) + " " + product_title + " " + str(tgturl['href']))

        # タグ抽出用関数に個別ページのURLを渡し、タグ群を取得
        title, tags = getAttributeTags(tgturl['href'])

        # {タグ, そのタグを発見した数}の形式で連想配列に格納。
        for tag in tags:
            att_dict[tag] = (att_dict.get(tag) or 0) + 1

        tags.insert(0, title)
        writer.writerow(tags)

        if (idx == 10) :
            break

        sleep(SCRAPING_INTERVAL_TIME)

    sleep(11)

f.close()

# 発見したタグとその数の一覧をCSV出力
f = open("TagList.csv", "w")
writer = csv.writer(f, lineterminator="\n")
header = ["Tag", "Count"]
writer.writerow(header)

csvline = []
for att in att_dict :
    csvline = [att, att_dict[att]]
    writer.writerow(csvline)

f.close()
