# coding: UTF-8
import requests
from bs4 import BeautifulSoup
import re # 正規表現用
from time import sleep      # 待ち時間用
from pprint import pprint  # 改行付き配列出力
import os.path # ファイル操作用
from datetime import datetime, timedelta, timezone
import subprocess # シェルスクリプト呼び出し用
import sys
import shutil   # ファイルコピー用
from functools import partial   # テキスト色変え用

RES_IN_SINGLEPAGE = 30
LOG_STORE_DIRECTORY = 'logs'
SCRAPING_INTERVAL_TIME = 3

NICOPEDI_URL_HEAD = "https://dic.nicovideo.jp/a/"

def CheckCreateDirectory(location, dirName) :

    relativePath = location + '/' + dirName

    if not os.path.exists(relativePath) :
        # ディレクトリが存在しない場合は作成
        os.mkdir(relativePath)
        print('Create',relativePath)

    return relativePath

# メイン記事のページャー部分からスクレイピング対象になる掲示板URLを取得する（既に取得済みの場合はそのIDからスタート）
def GetSearchTargetURLs(baseURL, latestId) :

    pageUrls = []

    # 対象記事トップへ移動し、HTMLパーサーで見る。
    tgtPage = requests.get(baseURL)
    soup = BeautifulSoup(tgtPage.content, "html.parser")

    # 記事タイトルが半角数値を含むとNaviタグの項目を拾ってしまうため除外
    soup.find('a', class_='navi').decompose()

    # ページャー部分を取得。
    pagers = soup.select("div.st-pg_contents")

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

    # ページは30*n+1で始まるので、「配列最後の要素[-1]から-1した値」を取ると最後のページ数がわかる。念の為Int化。
    # print(len(txts), txts[-1])
    finalPage = int((txts[-1] - 1) / RES_IN_SINGLEPAGE)
    finalPage += 1

    # 商を整数で取得（最新IDを1画面あたりのレス数で割ると何番目の頁から取得するのかがわかる）
    startPage = latestId // RES_IN_SINGLEPAGE

    # 記事本体のURLと掲示板用URLは微妙に異なるため修正。
    baseBbsUrl = baseURL.replace('/a/', '/b/a/')

    print(startPage * RES_IN_SINGLEPAGE, 'To', finalPage * RES_IN_SINGLEPAGE)
    # pprint(txts)

    # URLの末尾に[30x+1-]の値をつなげていくことで、取得対象となる画面のURLリストを取得する。
    for i in range(startPage, finalPage) :
        pageNum = i * RES_IN_SINGLEPAGE + 1
        pageUrl = baseBbsUrl + '/' + str(pageNum) + '-'
        pageUrls.append(pageUrl)


    return pageUrls

# 対象掲示板ページから全レスを取得する。
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
        h = h.getText()  # テキスト部分抽出
        h = h.replace('\n', '')  # 不要な改行を削除
        h = h.replace(' ', '')  # 不要な空白を削除
        h = h.replace(')', ') ')  # 整形
        h = h.replace('ID:', ' ID:')  # 整形
        formattedHead.append(h)

    # 整形済みレス本体部取得
    for rbody in resbodys:
        # レス本体部分をStr形式にキャスト、文字列置換で改行タグを改行コードに変換し再度bs4オブジェクトに戻す
        # これを行わないとWebページ上では改行されていた箇所が全部消えてあらゆるレスが１行になる
        b = str(rbody)
        b = b.replace("<br>", "\n")
        b = b.replace("<br/>", "\n")
        b = BeautifulSoup(b, "html.parser").getText()

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

# テキスト色変え用
def print_colored(code, text, is_bold=False):
    if is_bold:
        code = '1;%s' % code

    print('\033[%sm%s\033[0m' % (code, text))

print_red = partial(print_colored, '31')

# 入力したURLがニコニコ大百科内のものかチェック
def IsValidURL(targetURL) :
    isValid = targetURL.startswith(NICOPEDI_URL_HEAD)
    return isValid


# メイン処理スタート -----------------------------------------------------------------

# コマンドライン呼び出し時の引数取得
args = sys.argv

# args要素がゼロである(このファイルのみ)でキックされた場合は終了
if len(args) <= 1 :
    print_red('Nothing Target URL', is_bold=True)
    sys.exit(0)

tgtArtUrl = args[1]

# URLがニコ百科として不正な場合は終了
if not IsValidURL(tgtArtUrl) :
    print_red('This is not valid URL.', is_bold=True)
    print('Target URL should be under', NICOPEDI_URL_HEAD)
    sys.exit(0)

# ログ出力用ディレクトリを取得する。なければ作る。パーミッションについては考慮していない。
logDir = CheckCreateDirectory('.', LOG_STORE_DIRECTORY)

# 記事本体のデータを取得し、HTMLパーサで解釈
art_req = requests.get(tgtArtUrl)
art_soup = BeautifulSoup(art_req.content, 'html.parser')

# 取得したデータからカテゴリー要素を削除
art_soup.find('span', class_='st-label_title-category').decompose()
# よみがな部分を削除
art_soup.find('div', class_='a-title-yomi').decompose()
# 記事タイトルを取得（カテゴリが削除されていないとそれも含まれてしまう）
titleTxt = art_soup.find('div', class_='a-title')

# タイトル部のテキストを取得(記事タイトルになる)
pageTitle = titleTxt.getText()
# タイトル分前後に余計な空白・改行が入ってるケースがあるのでトリム
pageTitle = pageTitle.strip()
pageTitle = pageTitle.strip('\n')
# 半角スペースが入っていると面倒なので置換
pageTitle = pageTitle.replace(' ', '_')

# ログファイル名は「(記事タイトル).log」
pediLogFileName = pageTitle + ".log"
pediLogFileName = logDir + '/' + pediLogFileName

# Unixタイム(ミリ秒)を一時ファイルの名称として使用する
JST = timezone(timedelta(hours=+9), 'JST')
now = datetime.now(JST)
nowstamp = str(now.timestamp()).replace('.','')

# 一時メインファイル
tmpMainFile = nowstamp + '.main' + '.tmp'

# 対象ファイル削除 --------------------------------------------
# if os.path.exists(pediLogFileName) : os.remove(pediLogFileName)
# 対象ファイル削除 --------------------------------------------

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

# 現時点における最新IDから、取得を開始するべきURLを取得する。（スタート〜ラストを配列で取得）
targetURLs = GetSearchTargetURLs(tgtArtUrl, latestId)

# pprint(targetURLs)

# 新規に取るべき記事がない場合はその旨メッセージ出して終了。
if targetURLs == None :
    print("Nothing any response in Article")
    sys.exit(0)

# pprint(targetURLs)

print('Progress ... ', end='', flush=True)

for url in targetURLs:

    # インターバル中にファイルを掴みっぱなしなのは気持ち悪いからURL毎にオープン・クローズする(どっちがいいんだろう…)
    with open(tmpMainFile, 'a') as writer:

        # (当該ページにおいて)取得したレス数・整形した全ヘッダ部・整形した全レス本体部
        resCount, formattedHead, formattedBody = GetAllResInPage(url)

        # 途中スタートの場合、書き込むレスも途中からになる
        mark = (latestId % RES_IN_SINGLEPAGE)
        # ※最新取得が｢41｣だった場合、「31-」の記事における「11番目のレス」からスタートする。
        # その後続行する場合は最新IDは「60」で終わるので、「41-」の記事では「0番目のレス」からスタートする。

        # ヘッダ+本体の形で順に出力する。
        for i in range(mark, resCount):
            TeeOutput(formattedHead[i], writer)
            TeeOutput(formattedBody[i], writer)
            TeeOutput("", writer)
            latestId += 1

        # 動作検証中は最初のログを取ったところで止める。
        # if (latestId > 10) :
        #     break

        # ループ中に進捗確認用のテキスト出力。Flushがないと最後にまとめて吐き出される。
        print(latestId, end=' ', flush=True)

    # インターバルを入れる。最後のURLを取得した場合はスキップ。
    if url != targetURLs[-1] : sleep(SCRAPING_INTERVAL_TIME)

print()

# --------------------------------------------------------------
# 一時ヘッダーファイル用意
tmpHeadFile = nowstamp + '.head' + '.tmp'

with open(tmpHeadFile, 'w') as writer:
    metaInfo = [pageTitle, str(now.strftime("%Y-%m-%d/%H:%M")), str(latestId)]
    metaInfoLine = ' '.join(metaInfo)
    TeeOutput(metaInfoLine, writer)
# --------------------------------------------------------------
# 一時ヘッダ・一時メインファイルの結合。最終ログファイルを出力（シェルスクリプトで実装）
cmnd = ['./CatFiles.sh', tmpHeadFile, tmpMainFile, pediLogFileName]
subResult = subprocess.call(cmnd)
# --------------------------------------------------------------

print("Output =", pediLogFileName, '(', latestId, ')' )

# メイン処理エンド -----------------------------------------------------------------
