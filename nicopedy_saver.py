# coding: UTF-8
import requests
from bs4 import BeautifulSoup
import re # 正規表現用
from time import sleep      # 待ち時間用
from pprint import pprint  # 改行付き配列出力
import csv

SCRAPING_INTERVAL_TIME = 5.5

TARGET_ARTICLE_URL = "https://dic.nicovideo.jp/a/%E5%8F%A4%E8%B3%80%E8%91%B5"
# https://dic.nicovideo.jp/a/%E3%81%8B%E3%81%B0%E3%82%93%E3%81%95%E3%82%93"
# https://dic.nicovideo.jp/b/a/9.25%E3%E4%BB%B6/35251-
def getSearchTargetURLs(baseURL) :

    pageUrls = []

    # 対象記事トップへ移動し、HTMLパーサーで見る。
    tgtPage = requests.get(baseURL)
    soup = BeautifulSoup(tgtPage.content, "html.parser")
    # ページャー部分を取得。
    pagers = soup.select("div.pager")

    # 記事本体のURLと掲示板用URLは微妙に異なるため修正。
    baseBbsUrl = baseURL.replace('/a/', '/b/a/')
    # print(baseBbsUrl)

    # ここまでで同一内容のpager[0], pager[1]が手に入る。

    pager = pagers[0]

    # テキスト部分の取得
    pager = pager.getText()

    # 余計な空白の削除
    splitedTxt = pager.strip()
    # 改行で区切って配列へ格納
    splitedTxts = splitedTxt.split('\n')

    txts = []

    # 各要素へ実行
    for txt in splitedTxts :
        v = re.sub(r'\D', '', txt)  # 当該要素内から整数部分を抽出
        if v == '' : continue       # 要素が空白だった（整数がなかった）場合はスキップ
        txts.append(int(v))         # 整数値は最終配列へ格納。

    if len(txts) == 0 :
        return None

    pageCount = int((txts[-1] - 1) / 30)
    pageCount += 1

    for i in range(pageCount) :
        pageNum = 1 + (i * 30)
        pageUrl = baseBbsUrl + '/' + str(pageNum) + '-'
        pageUrls.append(pageUrl)

    return pageUrls


# メイン処理スタート

# file open
f = open("RankingList.csv", "w")
writer = csv.writer(f, lineterminator="\n")
header = ["Title", "Tags"]
writer.writerow(header)

att_dict = {}

art_req = requests.get(TARGET_ARTICLE_URL)
art_soup = BeautifulSoup(art_req.content, 'html.parser')

# 取得したデータからカテゴリー要素を削除
art_soup.find('span', class_='article-title-category').decompose()
# 記事タイトルを取得（カテゴリが削除されていないとそれも含まれてしまう）
titleTxt = art_soup.find('h1', class_='article-title')

print(titleTxt)
print(titleTxt.getText())
# titleTxt = titleTxt.find("span", class_="article-title-category").decompose()
# print(titleTxt)
# titleTxt = titleTxt.getText()
# print(titleTxt)

targetURLs = getSearchTargetURLs(TARGET_ARTICLE_URL)

for url in targetURLs:
    # print(url)

    # 対象URL
    r = requests.get(url)

    # 第一引数＝解析対象　第二引数＝パーサー(何を元に解析するか：この場合はHTML)
    soup = BeautifulSoup(r.content, "html.parser")

    resAll = soup.select("dl")
    # print(resAll)

    resheads = soup.find_all("dt", class_="reshead")
    resbodys = soup.find_all("dd", class_="resbody")

    formattedHead = []
    formattedBody = []
    resCount = 0
    i = 0

    for rhead in resheads :
        h = rhead
        h = h.getText()         # テキスト部分抽出
        h = h.replace('\n', '') # 不要な改行を削除
        h = h.replace(' ', '')  # 不要な空白を削除
        h = h.replace(')', ') ')        # 整形
        h = h.replace('ID:', ' ID')     # 整形
        formattedHead.append(h)

    for rbody in resbodys :
        b = rbody
        b = b.getText()
        b = b.strip()
        b = b.strip('\n')
        formattedBody.append(b)
        resCount += 1

    for i in range(resCount):
        print(formattedHead[i])
        print(formattedBody[i])
        print()

    # break

    # インターバルを入れる。最後のURLを取得した場合はスキップ。
    if url != targetURLs[-1] : sleep(SCRAPING_INTERVAL_TIME)

print("END")

f.close()
