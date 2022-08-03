import sys
sys.path.append(".\PlaySport_TaiwanWebCrawler_Gold")
import NBAWebCrawler
import EPLWebCrawler
import Ligue1WebCrawler
import LaLigaWebCrawler
import SerieAWebCrawler
import BundesligaWebCrawler
import NFLWebCrawler
import MLBWebCrawler
import CPBLWebCrawler
import NPBWebCrawler

def start():
    print('-' * 20)
    print('開始爬取NBA')
    print('-'*20)
    NBAWebCrawler.start()  # 一鍵執行程序
    print('-' * 20)
    print('開始爬取EPL')
    print('-'*20)
    EPLWebCrawler.start()  # 一鍵執行程序
    print('-' * 20)
    print('開始爬取Ligue1')
    print('-'*20)
    Ligue1WebCrawler.start()  # 一鍵執行程序
    print('-' * 20)
    print('開始爬取LaLiga')
    print('-'*20)
    LaLigaWebCrawler.start()  # 一鍵執行程序
    print('-' * 20)
    print('開始爬取SerieA')
    print('-'*20)
    SerieAWebCrawler.start()  # 一鍵執行程序
    print('-' * 20)
    print('開始爬取Bundesliga')
    print('-'*20)
    BundesligaWebCrawler.start()  # 一鍵執行程序
    print('-' * 20)
    print('開始爬取NFL')
    print('-'*20)
    NFLWebCrawler.start()  # 一鍵執行程序
    print('開始爬取MLB')
    print('-'*20)
    MLBWebCrawler.start()  # 一鍵執行程序
    print('開始爬取CPBL')
    print('-'*20)
    CPBLWebCrawler.start()  # 一鍵執行程序
    print('開始爬取NPB')
    print('-'*20)
    NPBWebCrawler.start()  # 一鍵執行程序

if __name__  ==  '__main__':
    start()