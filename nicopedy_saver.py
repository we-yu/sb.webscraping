# coding: UTF-8
import requests
from bs4 import BeautifulSoup
import re # 正規表現用
from time import sleep      # 待ち時間用
from pprint import pprint  # 改行付き配列出力
import csv
import os.path
import sys

SCRAPING_INTERVAL_TIME = 5.5

# TARGET_ARTICLE_URL = "https://dic.nicovideo.jp/a/%E5%8F%A4%E8%B3%80%E8%91%B5"
TARGET_ARTICLE_URL = "https://dic.nicovideo.jp/a/9.25%E3%81%91%E3%82%82%E3%83%95%E3%83%AC%E4%BA%8B%E4%BB%B6"

class MetaData :

    metaItems = {'updated':'UPDATE', 'threadId':'Thread ID', 'lastId':'Last ID'}

    # メタデータの項目部分を設定する
    def SetMetaTemplate(self) :
        print(self.metaItems['updated'])
        print(self.metaItems['threadId'])
        print(self.metaItems['lastId'])

        return

    # 対象ファイルへメタデータの値を入力する
    def SetMetaData(self) :
        return

    # 対象ファイルのメタデータの値を取得する
    def GetMetaData(self) :
        return


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

# ログ新規作成時の動作
def CreateLogFile(mt) :
    mt.SetMetaTemplate()
    return

# ログ追記時の動作
def AppendLogFile(mt) :
    mt.GetMetaData()
    return

# 標準出力とファイル出力を同時に行う。
def TeeOutput(text, file) :
    print(text + '\n', end="")
    file.write(text + '\n')
    return

# メイン処理スタート -----------------------------------------------------------------

art_req = requests.get(TARGET_ARTICLE_URL)
art_soup = BeautifulSoup(art_req.content, 'html.parser')

# 取得したデータからカテゴリー要素を削除
art_soup.find('span', class_='article-title-category').decompose()
# 記事タイトルを取得（カテゴリが削除されていないとそれも含まれてしまう）
titleTxt = art_soup.find('h1', class_='article-title')

# タイトル部のテキストを取得(記事タイトルになる)
pageTitle = titleTxt.getText()
print(pageTitle)

# ログファイル名は「(記事タイトル).txt」
pediLogFileName = pageTitle + ".txt"

# 対象ファイル削除
os.remove(pediLogFileName)

metas = MetaData()

# 対象記事へのログファイルが既に存在するかチェック。
if os.path.exists(pediLogFileName) :
    print("Found log file.")
    openMode = 'a'  # ファイル存在の場合は追記モード
    AppendLogFile(metas)
else :
    print("Not found log file.")
    openMode = 'w'  # ファイル無しの場合は作成モード
    CreateLogFile(metas)

# file open
writer = open(pediLogFileName, openMode)
writer.write(pageTitle + '\n\n')

targetURLs = getSearchTargetURLs(TARGET_ARTICLE_URL)

latestId = 0

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

    # 整形済みレスヘッダ部取得
    for rhead in resheads :
        h = rhead
        h = h.getText()         # テキスト部分抽出
        h = h.replace('\n', '') # 不要な改行を削除
        h = h.replace(' ', '')  # 不要な空白を削除
        h = h.replace(')', ') ')        # 整形
        h = h.replace('ID:', ' ID:')     # 整形
        formattedHead.append(h)

        # 当該レスのID番号を取得する

        # 整形済みレスヘッダ先頭の数値要素を取得(正規表現)
        repat = re.compile('^[0-9]*')
        thisId = repat.match(h)

        # 当該レスID番号取得(この時点における最新ID)
        latestId = int(thisId.group())

    # 整形済みレス本体部取得
    for rbody in resbodys :
        b = rbody
        b = b.getText()
        b = b.strip()       # 前後から空白削除
        b = b.strip('\n')   # 前後から改行削除
        formattedBody.append(b)
        # カウントするのはheadでもbodyでもどちらでもいいのだが、この数が本ページにおけるレス数になる(通常は30だが最終ページでは少ない可能性あり)
        resCount += 1

    # ヘッダ+本体の形で順に出力する。
    for i in range(resCount):
        TeeOutput(formattedHead[i], writer)
        TeeOutput(formattedBody[i], writer)
        TeeOutput("", writer)

    if (latestId > 20) :
        break

    # インターバルを入れる。最後のURLを取得した場合はスキップ。
    if url != targetURLs[-1] : sleep(SCRAPING_INTERVAL_TIME)

out = "Latest = " + str(latestId)
TeeOutput(out, writer)

writer.close()
# メイン処理エンド -----------------------------------------------------------------
