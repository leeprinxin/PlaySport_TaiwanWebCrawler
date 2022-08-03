import sys
sys.path.append(".\PlaySport_TaiwanWebCrawler")
from NBA import NBAWebCrawler
from datetime import datetime
import requests
import json,traceback

def send_JandiErrorsMessage(except_texts):
    webhook_url = 'https://wh.jandi.com/connect-api/webhook/25729815/ce8d5cca33dfef1a4e03d17287b66e72'
    DateTimeRange_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S.000")
    text = f'{DateTimeRange_string[:-4]}台灣運彩爬蟲端發生異常事件 :\n'
    text += f'Python File (TaiwanWebCrawler): NBAWebCrawler發生錯誤即通報報此異常訊息。\n'
    for except_text in except_texts:
        text += f"{except_text} \n "
    jandi_data = {"body": text,
                  "connectColor": "#e31724"}
    response = requests.post(webhook_url, data=json.dumps(jandi_data),headers={'Content-type': 'application/json'})
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )

def RUN_WebCrawler():
    nbawebcrawler= NBAWebCrawler()
    nbawebcrawler.start(MatchResultsSearchDays='3天') #天數 or 週 or 月份 EX. 1天, 3天, 1週, 3週, 1月, 2月, 3月 (type:str)

def start():
    except_texts = []
    try:
        RUN_WebCrawler()
    except:
        except_texts.append(traceback.format_exc())
        send_JandiErrorsMessage(except_texts)

if __name__ == '__main__':
    start()