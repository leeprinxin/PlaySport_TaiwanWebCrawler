import sys
sys.path.append(".\PlaySport_TaiwanWebCrawler_Gold")
from Bundesliga import BundesligaWebCrawler
from datetime import datetime
import requests
import json,traceback

def send_JandiErrorsMessage(except_texts):
    webhook_url = 'https://wh.jandi.com/connect-api/webhook/25729815/dacc290196a642c331c42b663b9d4728'

    DateTimeRange_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S.000")
    text = f'{DateTimeRange_string[:-4]}台灣運彩爬蟲端發生異常事件 :\n'
    text += f'Python File (TaiwanWebCrawler): BundesligaWebCrawler發生錯誤即通報報此異常訊息。\n'
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
    Bundesligawebcrawler= BundesligaWebCrawler()
    Bundesligawebcrawler.start(MatchResultsSearchDays='3天') #天數 or 週 or 月份 EX. 1天, 3天, 1週, 3週, 1月, 2月, 3月 (type:str)

def add_log(except_texts):
    with open('WebCrawler.txt','w') as f:
        f.write(f"{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}:\n ")
        for except_text in except_texts:
            f.write(f"{except_text} \n ")

def start():
    except_texts  = []
    try:
        RUN_WebCrawler()
    except:
        except_texts.append(traceback.format_exc())
        send_JandiErrorsMessage(except_texts)

if __name__ == '__main__':
    start()