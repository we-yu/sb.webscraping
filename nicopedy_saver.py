# coding: UTF-8
import requests
from bs4 import BeautifulSoup
import re # 正規表現用
from time import sleep      # 待ち時間用
from pprint import pprint  # 改行付き配列出力
import os.path
from datetime import datetime, timedelta, timezone
import subprocess
import sys
import shutil

RES_IN_SINGLEPAGE = 30
SCRAPING_INTERVAL_TIME = 6

TARGET_ARTICLE_URL = "https://dic.nicovideo.jp/a/%E5%8F%A4%E8%B3%80%E8%91%B5"

def getSearchTargetURLs(baseURL, latestId) :

    pageUrls = []

    # 対象記事トップへ移動し、HTMLパーサーで見る。
    tgtPage = requests.get(baseURL)
    soup = BeautifulSoup(tgtPage.content, "html.parser")

    # ページャー部分を取得。
    pagers = soup.select("div.pager")

    # 記事本体のURLと掲示板用URLは微妙に異なるため修正。
    baseBbsUrl = baseURL.replace('/a/', '/b/a/')

    # ここまでで同一内容のpager[0], pager[1]が手に入る。(ページネイション項目が二箇所あるため)
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

    # レスが存在しない場合はNone
    if len(txts) == 0 :
        return None

    # ページは30*n+1で始まるので、「最後の要素から-1した値」を取ると最後のページ数がわかる。念の為Int化。
    # print(len(txts), txts[-1])
    pageCount = int((txts[-1] - 1) / RES_IN_SINGLEPAGE)
    print(pageCount)
    pageCount += 1

    # pprint(txts)
    # pprint(pageCount)

    startPage = latestId // RES_IN_SINGLEPAGE

    for i in range(startPage, pageCount) :
        pageNum = txts[i]
        pageUrl = baseBbsUrl + '/' + str(pageNum) + '-'
        pageUrls.append(pageUrl)

    return pageUrls

def GetAllResInPage(tgtUrl) :
    # 対象URL
    r = requests.get(tgtUrl)

    # 第一引数＝解析対象　第二引数＝パーサー(何を元に解析するか：この場合はHTML)
    soup = BeautifulSoup(r.content, "html.parser")

    # resAll = soup.select("dl")
    # print(resAll)


    resheads = soup.find_all("dt", class_="reshead")
    resbodys = soup.find_all("dd", class_="resbody")

    formattedHead = []
    formattedBody = []
    resCount = 0

    # 整形済みレスヘッダ部取得
    for rhead in resheads:
        h = rhead
        h = h.getText()  # テキスト部分抽出
        h = h.replace('\n', '')  # 不要な改行を削除
        h = h.replace(' ', '')  # 不要な空白を削除
        h = h.replace(')', ') ')  # 整形
        h = h.replace('ID:', ' ID:')  # 整形
        formattedHead.append(h)

        # 当該レスのID番号を取得する

        # 整形済みレスヘッダ先頭の数値要素を取得(正規表現)
        # repat = re.compile('^[0-9]*')
        # thisId = repat.match(h)
        # 当該レスID番号取得(この時点における最新ID)
        # latestId = int(thisId.group())

    # 整形済みレス本体部取得
    i = 0
    for rbody in resbodys:
        b = rbody
        b = b.getText()
        b = b.strip()  # 前後から空白削除
        b = b.strip('\n')  # 前後から改行削除
        formattedBody.append(b)
        # カウントするのはheadでもbodyでもどちらでもいいのだが、この数が本ページにおけるレス数になる(通常は30だが最終ページでは少ない可能性あり)
        resCount += 1

    return resCount, formattedHead, formattedBody

# 標準出力とファイル出力を同時に行う。
def TeeOutput(text, file) :
    # print(text + '\n', end="")
    file.write(text + '\n')
    return

def GetLatestID(fName):
    try:
        cmnd = ['head', '-1', fName]
        subResult = subprocess.check_output(cmnd)
    except:
        print("Error.")

    heads = subResult.split()
    id = int(heads[2])

    return id

# メイン処理スタート -----------------------------------------------------------------

JST = timezone(timedelta(hours=+9), 'JST')
now = datetime.now(JST)
nowstamp = str(round(now.timestamp()))

art_req = requests.get(TARGET_ARTICLE_URL)
art_soup = BeautifulSoup(art_req.content, 'html.parser')

# 取得したデータからカテゴリー要素を削除
art_soup.find('span', class_='article-title-category').decompose()
# 記事タイトルを取得（カテゴリが削除されていないとそれも含まれてしまう）
titleTxt = art_soup.find('h1', class_='article-title')

# タイトル部のテキストを取得(記事タイトルになる)
pageTitle = titleTxt.getText()

# ログファイル名は「(記事タイトル).txt」
pediLogFileName = pageTitle + ".txt"

# 一時メインファイル
tmpMainFile = nowstamp + '.main' + '.tmp'

# 対象ファイル削除 --------------------------------------------
if os.path.exists(pediLogFileName) : os.remove(pediLogFileName)
# 対象ファイル削除 --------------------------------------------

# 対象記事へのログファイルが既に存在するかチェック。
if os.path.exists(pediLogFileName) :
    print("Found log file.")
    latestId = GetLatestID(pediLogFileName)
    openMode = 'a'
    shutil.copyfile(pediLogFileName, tmpMainFile)

else :
    print("Not found log file.")
    latestId = 0
    openMode = 'w'

writer = open(tmpMainFile, openMode)

if openMode == 'w' : TeeOutput(pageTitle + '\n', writer)

targetURLs = getSearchTargetURLs(TARGET_ARTICLE_URL, latestId)

if targetURLs == None :
    print("Nothing any response in Article")
    sys.exit(0)

pprint(targetURLs)

for url in targetURLs:

    resCount, formattedHead, formattedBody = GetAllResInPage(url)

    mark = (latestId % RES_IN_SINGLEPAGE)

    # ヘッダ+本体の形で順に出力する。
    for i in range(mark, resCount):
        TeeOutput(formattedHead[i], writer)
        TeeOutput(formattedBody[i], writer)
        TeeOutput("", writer)
        latestId += 1

    # if (latestId > 10) :
    #     break

    # インターバルを入れる。最後のURLを取得した場合はスキップ。
    if url != targetURLs[-1] : sleep(SCRAPING_INTERVAL_TIME)

writer.close()

# --------------------------------------------------------------
# 一時ヘッダーファイル用意
tmpHeadFile = nowstamp + '.head' + '.tmp'

writer = open(tmpHeadFile, 'w')
metaInfo = [pageTitle, str(now.strftime("%Y-%m-%d/%H:%M")), str(latestId)]
metaInfoLine = ' '.join(metaInfo)
TeeOutput(metaInfoLine, writer)
writer.close()
# --------------------------------------------------------------
# 一時ヘッダ・一時メインファイルの結合。最終ログファイルを出力（シェルスクリプトで実装）
cmnd = ['./CatFiles.sh', tmpHeadFile, tmpMainFile, pediLogFileName]
subResult = subprocess.call(cmnd)
# --------------------------------------------------------------

print("Page Name =", pageTitle)
print("Latest ID =", latestId)

# メイン処理エンド -----------------------------------------------------------------


