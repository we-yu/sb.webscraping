# coding: UTF-8
import requests
from bs4 import BeautifulSoup
import re # 正規表現用
from time import sleep      # 待ち時間用
from pprint import pprint   # 改行付き配列出力
import os.path # ファイル操作用
from datetime import datetime, timedelta, timezone
import subprocess # シェルスクリプト呼び出し用
import sys
import shutil   # ファイルコピー用
from functools import partial   # テキスト色変え用

FIXED_URL = "https://dic.nicovideo.jp/b/a/%E3%81%91%E3%82%82%E3%81%AE%E3%83%95%E3%83%AC%E3%83%B3%E3%82%BA2%E7%82%8E%E4%B8%8A%E4%BA%8B%E4%BB%B6"
RES_IN_SINGLEPAGE = 30          # 掲示板１頁あたりのレス数
LOG_STORE_DIRECTORY = 'logs'    # ログファイル保存ディレクトリ
SCRAPING_INTERVAL_TIME = 1      # スクレイピング時の休み時間

def GetURLs() :
    startPage = 0
    finalPage = int(32430 / RES_IN_SINGLEPAGE)

    pageUrls = []

    baseBbsUrl = FIXED_URL

    for i in range(startPage, finalPage) :
        pageNum = i * RES_IN_SINGLEPAGE + 1
        pageUrl = baseBbsUrl + '/' + str(pageNum) + '-'
        pageUrls.append(pageUrl)

    # pprint(pageUrls)
    return pageUrls

def CheckCreateDirectory(location, dirName) :

    relativePath = location + '/' + dirName

    if not os.path.exists(relativePath) :
        # ディレクトリが存在しない場合は作成
        os.mkdir(relativePath)
        # print('Create',relativePath)

    return relativePath

def TeeOutput(text, file) :
    # print(text + '\n', end="")
    file.write(text + '\n')
    return


def main() :
    GetURLs()

    # 記事タイトルを取得（カテゴリが削除されていないとそれも含まれてしまう）
    pageTitle = "KF2Flamed"

    # print("pageTitle = ", pageTitle ,":::")
    # タイトル分前後に余計な空白・改行が入ってるケースがあるのでトリム
    pageTitle = pageTitle.strip()
    pageTitle = pageTitle.strip('\n')
    # 半角スペースが入っていると面倒なので置換
    pageTitle = pageTitle.replace(' ', '_')

    logDir = CheckCreateDirectory('.', LOG_STORE_DIRECTORY)

    # ログファイル名は「(記事タイトル).log」
    pediLogFileName = pageTitle + ".log"
    pediLogFileName = logDir + '/' + pediLogFileName

    # Unixタイム(ミリ秒)を一時ファイルの名称として使用する
    JST = timezone(timedelta(hours=+9), 'JST')
    now = datetime.now(JST)
    nowstamp = str(now.timestamp()).replace('.','')

    # 一次ファイル格納用ディレクトリ生成
    tmpDir = CheckCreateDirectory('.', nowstamp)

    # 一時メインファイル
    tmpMainFile = tmpDir + '/' + nowstamp + '.main' + '.tmp'

    # 対象ファイル削除 --------------------------------------------
    # if os.path.exists(pediLogFileName) : os.remove(pediLogFileName)
    # 対象ファイル削除 --------------------------------------------

    print('Output log file = [', pediLogFileName, ']')

    # 対象記事へのログファイルが既に存在するかチェック。
    if os.path.exists(pediLogFileName) :
        # 既にログが存在する場合、取得済みの最新IDを取得
        # 追記モードになり、内容をそのままで一時ファイルとしてコピーする
        print("Found log file.")
        latestId = GetLatestID(pediLogFileName)
        openMode = 'a'
        shutil.copyfile(pediLogFileName, tmpMainFile)
    else :
        # 新規ログの場合、最新IDは0であり、書き込みモード
        print("Not found log file.")
        latestId = 0
        openMode = 'w'

    writer = open(tmpMainFile, openMode)
    # 追記モードの場合一行目にメタ情報が存在するため、位置をあわせるために新規ファイルの戦闘に空白行を入れておく
    if openMode == 'w' : TeeOutput(pageTitle + '\n', writer)
    writer.close()

    targetURLs = GetURLs()

    # 新規に取るべき記事がない場合は終了。
    if targetURLs == None :
        sys.exit(0)

    print('Progress ... ', end='', flush=True)

    for url in targetURLs:

        # インターバル中にファイルを掴みっぱなしなのは気持ち悪いからURL毎にオープン・クローズする(どっちがいいんだろう…)
        with open(tmpMainFile, 'a') as writer:

            # (当該ページにおいて)取得したレス数・整形した全ヘッダ部・整形した全レス本体部
            resCount, formattedHead, formattedBody = GetAllResInPage(url)

            # 途中スタートの場合、書き込むレスも途中からになる
            mark = (latestId % RES_IN_SINGLEPAGE)
            # ※最新取得が｢41｣だった場合、「31-」の記事における「11番目のレス」からスタートする。
            # その後続行する場合は最新IDは「60」で終わるので、「61-」の記事では「0番目のレス」からスタートする。

            # ヘッダ+本体の形で順に出力する。
            for i in range(mark, resCount):
                TeeOutput(formattedHead[i], writer)
                TeeOutput(formattedBody[i], writer)
                TeeOutput("", writer)
                latestId += 1

            # 動作検証中は最初のログを取ったところで止める。
            # if (latestId > 300) :
            #     break

            # ループ中に進捗確認用のテキスト出力。Flushがないと最後にまとめて吐き出される。
            print(latestId, end=' ', flush=True)

        # インターバルを入れる。最後のURLを取得した場合はスキップ。
        if url != targetURLs[-1] : sleep(SCRAPING_INTERVAL_TIME)

    print()

    # --------------------------------------------------------------
    # 一時ヘッダーファイル用意
    tmpHeadFile = tmpDir + '/' + nowstamp + '.head' + '.tmp'

    with open(tmpHeadFile, 'w') as writer:
        metaInfo = [pageTitle, str(now.strftime("%Y-%m-%d/%H:%M")), str(latestId)]
        metaInfoLine = ' '.join(metaInfo)
        TeeOutput(metaInfoLine, writer)
    # --------------------------------------------------------------
    # 一時ヘッダ・一時メインファイルの結合。最終ログファイルを出力（シェルスクリプトで実装）
    headlessFile = tmpDir + '/' + 'headless' + '.tmp'
    cmnd = ['./CatFiles.sh', tmpHeadFile, tmpMainFile, headlessFile, pediLogFileName]
    # pprint(cmnd)
    subResult = subprocess.call(cmnd)
    # --------------------------------------------------------------
    # 一時ファイル格納用ディレクトリの削除(中身ごと)
    shutil.rmtree(tmpDir)

    print("Output =", pediLogFileName, '(', latestId, ')' )

def GetAllResInPage(tgtUrl) :
    # 対象URL
    r = requests.get(tgtUrl)

    # 第一引数＝解析対象　第二引数＝パーサー(何を元に解析するか：この場合はHTML)
    soup = BeautifulSoup(r.content, "html.parser")

    # dt, ddタグ以下の特定クラスをかき集める。
    resheads = soup.find_all("dt", class_="st-bbs_reshead")
    resbodys = soup.find_all("dd", class_="st-bbs_resbody")

    formattedHead = []
    formattedBody = []
    resCount = 0

    # 整形済みレスヘッダ部取得
    for rhead in resheads:
        h = rhead

        # 取得したdt情報を再度文字列化し、BeautifulSoupにかけることでdt以下のタグを同じ手法で取れるようにする
        hObj = BeautifulSoup(str(h), 'html.parser')

        # dtタグ内における各タグ(およびクラス)を取得
        bbs_resNo   = hObj.find('span', class_='st-bbs_resNo').getText()
        bbs_name    = hObj.find('span', class_='st-bbs_name').getText()
        bbs_resInfo = hObj.find('div', class_='st-bbs_resInfo').getText()
        # resInfo情報に関しては調整が必要なので前後のトリム・改行コードのち缶等を調整する
        bbs_resInfo = bbs_resInfo.strip()
        bbs_resInfo = bbs_resInfo.strip('\n')
        bbs_resInfo = bbs_resInfo.replace('\n', ' ')

        # テキスト中に大量の空白が混ざっているため、正規表現で複数空白については空白一個に置換する
        pattern = r' +'
        bbs_resInfo = re.sub(pattern, ' ', bbs_resInfo)
        # print(bbs_resNo, bbs_name, bbs_resInfo)
        # やり方はなんでもいいのだが、取得した複数のテキストを空白で区切った一行に出力。整形済みヘッダhへappendする
        resHeaders = [bbs_resNo, bbs_name, bbs_resInfo]
        h = ' '.join(resHeaders)

        formattedHead.append(h)

    # 整形済みレス本体部取得
    for rbody in resbodys:
        # レス本体部分をStr形式にキャスト、文字列置換で改行タグを改行コードに変換し再度bs4オブジェクトに戻す
        # これを行わないとWebページ上では改行されていた箇所が全部消えてあらゆるレスが１行になる
        b = str(rbody)
        b = b.replace("<br>", "\n")
        b = b.replace("<br/>", "\n")
        b = BeautifulSoup(b, "html.parser").getText()

        b = b.strip()       # 前後から空白削除
        b = b.strip('\n')   # 前後から改行削除
        formattedBody.append(b)
        # カウントするのはheadでもbodyでもどちらでもいいのだが、この数が本ページにおけるレス数になる(通常は30だが最終ページでは少ない可能性あり)
        resCount += 1

    return resCount, formattedHead, formattedBody

if __name__ == "__main__" :
    main()
