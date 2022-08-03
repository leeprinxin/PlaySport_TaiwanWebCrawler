import requests,bs4
import json
from datetime import datetime
from datetime import datetime,timezone,timedelta
import traceback, pymssql
import time
from selenium import webdriver
import selenium
from selenium.webdriver.firefox.options import Options
from time import sleep
from urllib.parse import urlparse
from urllib.parse import parse_qs
import pytz
utc = pytz.UTC

import sys
sys.path.append(".\PlaySport_TaiwanWebCrawler_Gold")
import Config

class MLBWebCrawler(object):
    def __init__(self):
        # 即將舉行的比賽
        days = [datetime.now().strftime('%Y%m%d'), (datetime.now()+timedelta(days=1)).strftime('%Y%m%d')]
        self.MLB_UpcomingMacths_URLs = [f"https://www.playsport.cc/predictgame.php?allianceid={1}&gametime={day}" for day in days]

        self.headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36'}
        self.SourceCode = 'Taiwan' # 台灣運彩編碼
        self.SportCode = 3 # 棒球運動編碼: 2 來自SportCode table
        self.SportTournamentCode = '10041830' # 沿用
        self.EventType = 0
        self.CollectClient = 'MLB'
        self.server = "guess365.database.windows.net"
        self.database = 'Guess365'
        self.user = 'crawl'
        self.password = 'DataToGuess365@user1'
        self.Games = '21' # 運動聯盟編號
        self.SportText = 'Baseball'
        self.TournamentText = 'MLB'

    def start(self, MatchResultsSearchDays = '1天'):
        self.executable_path = Config.executable_path
        print(self.executable_path)
        self.MatchEntry = []
        self.Odds = {}
        self.get_MatchEntry()
        self.get_Odds()
        self.add_MatchEntry_or_Odds()
        self.MatchResults = []
        self.get_MatchResultsBySelenium(day = MatchResultsSearchDays)
        self.add_MatchResults()

    def get_ConnectionFromDB(self):
        db = pymssql.connect(self.server,self.user,self.password,self.database)
        cursor = db.cursor()
        return db, cursor

    def add_MatchResults(self):
        if self.MatchResults == []:
            print('MatchResults尚未進行爬蟲或無資料')
            return
        db, cursor = self.get_ConnectionFromDB()
        for MatchResult in self.MatchResults:
                try:
                   insert_sql = f'''INSERT INTO [dbo].[MatchResults] ([EventCode],[TournamentText],[MatchTime],[HomeTeam]
                                                 ,[AwayTeam],[HomeScore],[AwayScore],[EndTime],[time_status],[error_log]) VALUES
                                         ('{MatchResult['EventCode']}','{MatchResult['TournamentText']}','{MatchResult['MatchTime']}','{MatchResult['HomeTeam']}',
                                         '{MatchResult['AwayTeam']}','{MatchResult['HomeScore']}','{MatchResult['AwayScore']}','{MatchResult['EndTime']}',
                                         '{MatchResult['time_status']}','{MatchResult['error_log']}')'''
                   print('執行:',insert_sql)
                   cursor.execute(insert_sql)
                   db.commit()
                except:
                    print('目前MatchEntry尚無對應賽事或已經有重複賽事')

    def get_MatchResultsBySelenium(self, day = '1天'):
        """
        從https://www.sportslottery.com.tw/zh-tw/game/pre取得NBA今日結束比賽
        :param 
        :return: 
        """
        print('*'*20,'get_MatchResults','*'*20)
        url = 'https://www.sportslottery.com.tw/zh-tw/result'
        useragent = "Mozilla/5.0 (Linux; Android 8.0.0; Pixel 2 XL Build/OPD1.170816.004) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Mobile Safari/537.36"
        profile = webdriver.FirefoxProfile()
        profile.set_preference("general.useragent.override", useragent)
        options = webdriver.FirefoxOptions()
        options.set_preference("dom.webnotifications.serviceworker.enabled", False)
        options.set_preference("dom.webnotifications.enabled", False)
        options.add_argument('--headless')
        if self.executable_path == '':
            browser = webdriver.Firefox(firefox_profile=profile, options=options)
        else:
            browser = webdriver.Firefox(firefox_profile=profile, options=options, executable_path=self.executable_path)
        browser.get(url)

        sleep(1)
        browser.find_elements_by_css_selector("div.tslc-tabs-item")[1].click()
        sleep(1)
        browser.find_element_by_xpath("//option[contains(text(),'棒球')]").click()
        sleep(1)
        browser.find_element_by_xpath("//option[contains(text(),'美國')]").click()
        sleep(1)
        browser.find_element_by_xpath("//option[contains(text(),'美國職棒')]").click()
        sleep(1)
        browser.find_element_by_xpath(f"//option[contains(text(),'{day}')]").click()
        sleep(1)
        browser.find_element_by_xpath("//body/div[1]/div[1]/div[2]/div[1]/div[4]/div[1]/input[1]").click()
        sleep(2)
        try:
          db, cursor = self.get_ConnectionFromDB()
          while True:
              objSoup = bs4.BeautifulSoup(browser.find_element_by_xpath('//*').get_attribute('outerHTML'), 'lxml')
              for table, mydate  in zip(objSoup.select('div.tslc-search-2 div.tslc-search-result div.table-responsive')[:],objSoup.select("div.tslc-search-2 div.tslc-search-result div.tslc-date")[:]):
                  tbodys = table.select('table tbody')
                  mydate = mydate.text.split(' ')[0].strip()

                  for tbody in tbodys:
                    games = tbody.select('tr[class]')
                    if len(games) <2:
                        continue
                    for i in range(0,len(games),2):
                        tds_a = games[i].find_all('td')
                        tds_h = games[i+1].find_all('td')

                        HomeTeam = self.TeamNameCorrection(tds_h[1].text.split('(')[0].strip(),cursor,1)
                        AwayTeam = self.TeamNameCorrection(tds_a[4].text.split('(')[0].strip(),cursor,1)

                        MatchTime = datetime.strptime(mydate+' '+tds_a[0].text+':00', "%Y/%m/%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S.000")
                        MatchTime = self.MatchTimeCorrection(MatchTime,30,HomeTeam,AwayTeam,cursor)


                        EndTime = self.CollectedTime # self.getEndTime(MatchTime, 30, tds_h[1].text,tds_a[4].text,tds_a[2].text,cursor)

                        EventCode_Prefix = self.Games + '_' + MatchTime.strftime("%Y%m%d") + '_'  # 聯盟編號_比賽日期 ex. 2_20211213
                        EventCode = EventCode_Prefix + str(tds_a[2].text)
                        HomeScore = tds_h[-1].text
                        AwayScore = tds_a[-1].text
                        if (not HomeScore.isdigit()) or (not AwayScore.isdigit()):
                            continue

                        MatchResult = dict(EventCode=EventCode,TournamentText=self.TournamentText,MatchTime=MatchTime
                            ,HomeTeam=HomeTeam,AwayTeam=AwayTeam,HomeScore=HomeScore,AwayScore=AwayScore
                            ,EndTime=EndTime,time_status='Ended',error_log='None')
                        self.MatchResults.append(MatchResult)
                        print('爬取內容:',MatchResult)
              sleep(2)
              browser.find_element_by_xpath("//a[contains(text(),'下一頁')]").click()

        except selenium.common.exceptions.NoSuchElementException:
            print('尚無下一頁')
            cursor.close()
            db.close()

            browser.close()
            browser.quit()
        except:
            print(traceback.format_exc())
            cursor.close()
            db.close()

    def is_MatchEntry_existed(self, cursor, EventCode):
        '''
        根據EventCode查詢比賽是否存在
        :param cursor:SQL指標物件, EventCode:比賽識別碼
        :return True:存在, False:不存在
        '''
        sql = f'''SELECT * FROM [dbo].[MatchEntry] where EventCode = '{EventCode}' '''
        print('執行:',sql)
        cursor.execute(sql)
        results = cursor.fetchall()
        if len(results)>0:
            print(f"編號{EventCode}已經存在")
            return True
        else:
            print(f"編號{EventCode}不存在")
            return False

    def is_Odds_existed(self,cursor,play):
        sql = f"SELECT id FROM [dbo].[Odds] where GroupOptionCode = {play['GroupOptionCode']} AND EventCode = '{play['EventCode']}' AND OptionCode='{play['OptionCode']}' "
        print('執行:',sql)

        cursor.execute(sql)
        results = cursor.fetchall()
        if len(results)>0:
            print(f"編號{play['EventCode']}的玩法{play['GroupOptionCode']}已經存在")
            return True
        else:
            print(f"編號{play['EventCode']}的玩法{play['GroupOptionCode']}不存在")
            return False
        
    def add_MatchEntry_or_Odds(self):
        print('*'*20,'add_MatchEntry_or_Odds','*'*20)
        if self.Odds == {} or self.MatchEntry == [] :
            print('Odds or MatchEntry尚未進行爬蟲或無資料') 
            return
        
        db, cursor = self.get_ConnectionFromDB()
        for game_dict in self.MatchEntry:
            if not self.is_MatchEntry_existed(cursor,game_dict['EventCode']): # 若比賽不存在，則MatchEntry與Odds寫入資料庫
                 insert_sql = f'''INSERT INTO [dbo].[MatchEntry]([SportText],[TournamentText],[HomeTeam],[AwayTeam],[Score],[MatchTime],[HomePitcher],[AwayPitcher],[SourceCode],[SportCode],[SportTournamentCode],[EventCode],[EventType],[CollectClient],[CollectedTime],[CreatedTime])VALUES
                                       ('{game_dict['SportText']}','{game_dict['TournamentText']}','{game_dict['HomeTeam']}','{game_dict['AwayTeam']}','{game_dict['Score']}','{game_dict['MatchTime']}',N'{game_dict['HomePitcher']}',N'{game_dict['AwayPitcher']}','{game_dict['SourceCode']}','{game_dict['SportCode']}','{game_dict['SportTournamentCode']}','{game_dict['EventCode']}','{game_dict['EventType']}','{game_dict['CollectClient']}','{game_dict['CollectedTime']}','{game_dict['CreatedTime']}')'''
                 print('執行:',insert_sql)
                 cursor.execute(insert_sql)
                 db.commit()
                 plays = self.Odds[game_dict['EventCode']]
                 if len(plays)< 1:
                    print(f"編號:{game_dict['EventCode']}尚無玩法")
                 for play in plays:
                     insert_sql = f'''INSERT INTO [dbo].[Odds]([GroupOptionCode],[OptionCode],[SpecialBetValue],[OptionRate],[SourceCode],[SportCode],[SportTournamentCode],[EventCode],[EventType],[CollectClient],[CollectedTime],[CreatedTime])VALUES
                                       ('{play['GroupOptionCode']}','{play['OptionCode']}','{play['SpecialBetValue']}','{play['OptionRate']}',
                                       '{play['SourceCode']}','{play['SportCode']}','{play['SportTournamentCode']}','{play['EventCode']}','{play['EventType']}','{game_dict['CollectClient']}','{game_dict['CollectedTime']}','{game_dict['CreatedTime']}')'''
                     print('執行:',insert_sql)
                     cursor.execute(insert_sql)
                     db.commit()

                     insert_sql = f'''INSERT INTO [dbo].[OddsEntry]([GroupOptionCode],[OptionCode],[SpecialBetValue],[OptionRate],[SourceCode],[SportCode],[SportTournamentCode],[EventCode],[EventType],[CollectClient],[CollectedTime],[CreatedTime])VALUES
                                       ('{play['GroupOptionCode']}','{play['OptionCode']}','{play['SpecialBetValue']}','{play['OptionRate']}',
                                       '{play['SourceCode']}','{play['SportCode']}','{play['SportTournamentCode']}','{play['EventCode']}','{play['EventType']}','{game_dict['CollectClient']}','{game_dict['CollectedTime']}','{game_dict['CreatedTime']}')'''
                     print('執行:',insert_sql)
                     cursor.execute(insert_sql)
                     db.commit()

            else: # 若比賽存在，則MatchEntry更新
                 update_sql = f'''UPDATE [dbo].[MatchEntry] SET [MatchTime]='{game_dict['MatchTime']}',[HomePitcher]=N'{game_dict['HomePitcher']}',[AwayPitcher]=N'{game_dict['AwayPitcher']}' WHERE [EventCode] = '{game_dict['EventCode']}' '''
                 print('執行:',update_sql)
                 cursor.execute(update_sql)

                 plays = self.Odds[game_dict['EventCode']] # 提取每場比賽玩法
                 if len(plays)< 1:
                    print(f"編號:{game_dict['EventCode']}尚無玩法")

                 for play in plays:
                     if not self.is_Odds_existed(cursor,play):
                         '''
                         寫入Odds OddsEntry
                         '''
                         insert_sql = f'''INSERT INTO [dbo].[Odds]([GroupOptionCode],[OptionCode],[SpecialBetValue],[OptionRate],[SourceCode],[SportCode],[SportTournamentCode],[EventCode],[EventType],[CollectClient],[CollectedTime],[CreatedTime])VALUES
                                           ('{play['GroupOptionCode']}','{play['OptionCode']}','{play['SpecialBetValue']}','{play['OptionRate']}',
                                           '{play['SourceCode']}','{play['SportCode']}','{play['SportTournamentCode']}','{play['EventCode']}','{play['EventType']}','{game_dict['CollectClient']}','{game_dict['CollectedTime']}','{game_dict['CreatedTime']}')'''
                         print('執行:',insert_sql)
                         cursor.execute(insert_sql)
                         db.commit()

                         insert_sql = f'''INSERT INTO [dbo].[OddsEntry]([GroupOptionCode],[OptionCode],[SpecialBetValue],[OptionRate],[SourceCode],[SportCode],[SportTournamentCode],[EventCode],[EventType],[CollectClient],[CollectedTime],[CreatedTime])VALUES
                                           ('{play['GroupOptionCode']}','{play['OptionCode']}','{play['SpecialBetValue']}','{play['OptionRate']}',
                                           '{play['SourceCode']}','{play['SportCode']}','{play['SportTournamentCode']}','{play['EventCode']}','{play['EventType']}','{game_dict['CollectClient']}','{game_dict['CollectedTime']}','{game_dict['CreatedTime']}')'''
                         print('執行:',insert_sql)
                         cursor.execute(insert_sql)
                         db.commit()

                     else:
                         '''
                         更新Odds 寫入OddsEntry
                         '''
                         update_sql = f'''UPDATE [dbo].[Odds] SET [GroupOptionCode]='{play['GroupOptionCode']}',[OptionCode]='{play['OptionCode']}',[SpecialBetValue]='{play['SpecialBetValue']}',[OptionRate]='{play['OptionRate']}',
                                             [SourceCode]='{play['SourceCode']}',[SportCode]='{play['SportCode']}',[SportTournamentCode]='{play['SportTournamentCode']}',[EventCode]='{play['EventCode']}',[EventType]='{play['EventType']}'
                                             ,[CollectClient]='{game_dict['CollectClient']}',[CollectedTime]='{game_dict['CollectedTime']}',[CreatedTime]='{game_dict['CreatedTime']}' 
                                              WHERE GroupOptionCode='{play['GroupOptionCode']}' AND EventCode='{play['EventCode']}' AND OptionCode='{play['OptionCode']}'  '''
                               
                         print('執行:',update_sql)
                         cursor.execute(update_sql)
                         db.commit()

                         insert_sql = f'''INSERT INTO [dbo].[OddsEntry]([GroupOptionCode],[OptionCode],[SpecialBetValue],[OptionRate],[SourceCode],[SportCode],[SportTournamentCode],[EventCode],[EventType],[CollectClient],[CollectedTime],[CreatedTime])VALUES
                                           ('{play['GroupOptionCode']}','{play['OptionCode']}','{play['SpecialBetValue']}','{play['OptionRate']}',
                                           '{play['SourceCode']}','{play['SportCode']}','{play['SportTournamentCode']}','{play['EventCode']}','{play['EventType']}','{game_dict['CollectClient']}','{game_dict['CollectedTime']}','{game_dict['CreatedTime']}')'''
                         print('執行:',insert_sql)
                         cursor.execute(insert_sql)
                         db.commit()
            
 
        
        cursor.close()
        db.close()

    def get_Odds(self):
        '''
        QueryGroupOptionCode   type  QueryOptionCode
        20            home  1
        20            away  2
        228            home  1
        228            away  2
        60            Over  Over
        60            Under  Under
        :param 
        :return: 
        '''
        print('*'*20,'get_Odds','*'*20)
        if self.MatchEntry == []:
            print('MatchEntry尚未進行爬蟲或尚無資料')
            return 
        
        QueryGroupOptionCode = {'td-bank-bet03':20,'td-bank-bet01':228,'td-bank-bet02':60}
        QueryOptionCode = {'20,home':1,'20,away':2,'228,home':1,'228,away':2,'60,Over':'Over','60,Under':'Under'}

        factor = 0 # 賠率因子
        for game_dict in self.MatchEntry:
            Odds_html = game_dict['Odds_html']
            for away_odds_html,home_odds_html  in zip(Odds_html[0],Odds_html[1]):
                try:
                    GroupOptionCode = QueryGroupOptionCode[f"{away_odds_html['class'][0]}"]
                    print(f"編號{game_dict['EventCode']}爬取玩法:",GroupOptionCode)
                    if GroupOptionCode == 20:
                        OptionCode_H = QueryOptionCode[f"{GroupOptionCode},home"]
                        OptionCode_A = QueryOptionCode[f"{GroupOptionCode},away"]
                        SpecialBetValue_H = ''
                        SpecialBetValue_A = ''
                        OptionRate_H = home_odds_html.div.label.span.span.getText()
                        OptionRate_A = away_odds_html.div.label.span.span.getText()
                    elif GroupOptionCode == 228:
                        OptionCode_H  = QueryOptionCode[f"{GroupOptionCode},home"]
                        OptionCode_A = QueryOptionCode[f"{GroupOptionCode},away"]
                        SpecialBetValue_H = home_odds_html.div.label.span.strong.getText()
                        SpecialBetValue_A = home_odds_html.div.label.span.strong.getText()
                        OptionRate_H = home_odds_html.div.label.span.span.getText().split(',')[1].strip()
                        OptionRate_A = away_odds_html.div.label.span.span.getText().split(',')[1].strip() # 以主場賠率為主
                    elif GroupOptionCode == 60:
                        OptionCode_H  = QueryOptionCode[f"{GroupOptionCode},Under"]
                        OptionCode_A = QueryOptionCode[f"{GroupOptionCode},Over"]
                        SpecialBetValue_H = home_odds_html.div.label.span.strong.getText()
                        SpecialBetValue_A = away_odds_html.div.label.span.strong.getText()
                        OptionRate_H =  home_odds_html.div.label.span.span.getText().split(',')[1].strip()
                        OptionRate_A =  away_odds_html.div.label.span.span.getText().split(',')[1].strip()

                    SourceCode = self.SourceCode
                    SportCode = self.SportCode
                    SportTournamentCode = self.SportTournamentCode
                    EventCode = game_dict['EventCode']
                    EventType = self.EventType
                    CollectClient = self.CollectClient
                    CollectedTime = self.CollectedTime
                    CreatedTime = datetime.now().astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S.000")
                    play_dict_H = dict(GroupOptionCode=GroupOptionCode,OptionCode=OptionCode_H,SpecialBetValue=SpecialBetValue_H,OptionRate=OptionRate_H,SourceCode=SourceCode,SportCode=SportCode,SportTournamentCode=SportTournamentCode,EventCode=EventCode,EventType=EventType,CollectClient=CollectClient,CollectedTime=CollectedTime,CreatedTime=CreatedTime)
                    play_dict_A = dict(GroupOptionCode=GroupOptionCode,OptionCode=OptionCode_A,SpecialBetValue=SpecialBetValue_A,OptionRate=OptionRate_A,SourceCode=SourceCode,SportCode=SportCode,SportTournamentCode=SportTournamentCode,EventCode=EventCode,EventType=EventType,CollectClient=CollectClient,CollectedTime=CollectedTime,CreatedTime=CreatedTime)
                    try:
                        self.Odds[game_dict['EventCode']] = self.Odds[game_dict['EventCode']] + [play_dict_H,play_dict_A]
                    except:
                        self.Odds[game_dict['EventCode']]= [play_dict_H,play_dict_A]

                except:
                    print('不支援此玩法')
                    #print(traceback.format_exc())

            try:
                print(f"{game_dict['EventCode']}有{len(self.Odds[game_dict['EventCode']])//2}種玩法")
            except:
                print(f"編號{game_dict['EventCode']}有{0}種玩法")
                self.Odds[game_dict['EventCode']] = []
            print('*'*20)

    def MatchTimeCorrection(self,mydatatime, offset_minute, HomeTeam, AwayTeam, cursor):
        offset_sec = offset_minute*60
        d = datetime.strptime(mydatatime, "%Y-%m-%d %H:%M:%S.000")
        timestamp = time.mktime(d.timetuple())
        top = datetime.fromtimestamp(timestamp+offset_sec).strftime("%Y-%m-%d %H:%M:%S")
        bottom = datetime.fromtimestamp(timestamp-offset_sec).strftime("%Y-%m-%d %H:%M:%S")
         
        sql = f"SELECT MatchTime FROM MatchEntry where SourceCode = 'Bet365' AND MatchTime > '{bottom}' AND MatchTime < '{top}' AND HomeTeam = '{HomeTeam}' AND AwayTeam = '{AwayTeam}' "
        print('執行',sql)
        cursor.execute(sql)
        result = cursor.fetchone()
        if result:
            print(f"更換為Bet365時間")
            return result[0]
        else:
            print(f"更換為Taiwan時間")
            return datetime.strptime(mydatatime, "%Y-%m-%d %H:%M:%S.000")
        
    def getEndTime(self,mydatatime, offset_minute, HomeTeam, AwayTeam, EventCode, cursor):
        offset_sec = offset_minute*60
        d = datetime.strptime(mydatatime, "%Y-%m-%d %H:%M:%S.000")
        timestamp = time.mktime(d.timetuple())
        top = datetime.fromtimestamp(timestamp+offset_sec).strftime("%Y-%m-%d %H:%M:%S")
        bottom = datetime.fromtimestamp(timestamp-offset_sec).strftime("%Y-%m-%d %H:%M:%S")
         
        sql = f"SELECT EndTime FROM MatchResults where   MatchTime > '{bottom}' AND MatchTime < '{top}' AND HomeTeam = '{HomeTeam}' AND AwayTeam = '{AwayTeam}' "
        print('執行',sql)
        cursor.execute(sql)
        result = cursor.fetchone()
        if result:
            print(f"編號{EventCode}更換為Bet365結束時間")
            return result[0]
        else:
            print(f"編號{EventCode}更換為Taiwan結束時間")
            return datetime.strptime(mydatatime, "%Y-%m-%d %H:%M:%S.000")

    def TeamNameCorrection(self,Taiwan_TeamName, cursor, byChinese=0):
        if byChinese:
            sql = f"SELECT  team FROM teams  where name = N'{Taiwan_TeamName}' "
        else:
            sql = f"SELECT teams.team FROM teamText join teams on teamText.team_id = teams.id where Text = '{Taiwan_TeamName}' ;"
        cursor.execute(sql)
        result = cursor.fetchone()
        if result:
            #print(f'{Taiwan_TeamName}更換名稱為{result[0]}')
            return result[0]
        else:
            return Taiwan_TeamName    

    def get_Alliance(self, TeamName, cursor):
        sql = f'''SELECT Games.game FROM [dbo].TeamGame inner join teams on teams.id = TeamGame.team_id inner join Games on TeamGame.game_id = Games.id where teams.team = '{TeamName}' '''
        cursor.execute(sql)
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return ''

    def get_MatchEntry(self):
        """
        從https://www.playsport.cc/predictgame.php?allianceid=3&from=header取得NBA所有比賽
        :param 
        :return: 
        """
        print('*' * 20, 'get_MatchEntry', '*' * 20)
        self.CollectedTime = datetime.now().astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S.000")
        db, cursor = self.get_ConnectionFromDB()

        useragent = "Mozilla/5.0 (Linux; Android 8.0.0; Pixel 2 XL Build/OPD1.170816.004) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Mobile Safari/537.36"
        profile = webdriver.FirefoxProfile()
        profile.set_preference("general.useragent.override", useragent)
        options = webdriver.FirefoxOptions()
        options.set_preference("dom.webnotifications.serviceworker.enabled", False)
        options.set_preference("dom.webnotifications.enabled", False)
        options.add_argument('--headless')
        if self.executable_path == '':
            browser = webdriver.Firefox(firefox_profile=profile, options=options)
        else:
            browser = webdriver.Firefox(firefox_profile=profile, options=options, executable_path=self.executable_path)

        for url in self.MLB_UpcomingMacths_URLs:
            browser.get(url)
            time.sleep(3)
            objSoup = bs4.BeautifulSoup(browser.find_element_by_xpath('//*').get_attribute('outerHTML'), 'lxml')
            games = objSoup.select('table.predictgame-table tbody tr[gameid]')

            for i in range(0,len(games),2):
                # 取得比賽時間
                parsed_url = urlparse(url)
                gameday = parse_qs(parsed_url.query)['gametime'][0]
                MatchTime = gameday + ' ' + games[i].select('td.td-gameinfo')[0].div.h4.getText().strip()
                MatchTime = datetime.strptime(MatchTime,'%Y%m%d %p %I:%M')

                if not games[i].select('td.td-teaminfo')[0].has_attr('rowspan') and datetime.now().astimezone(timezone(timedelta(hours=8))).replace(tzinfo=utc) <= MatchTime.replace(tzinfo=utc): #檢查是否完賽或開賽中
                    # 取得隊伍
                    AwayTeam =  self.TeamNameCorrection(games[i].select('td.td-teaminfo div h3')[0].getText().strip(), cursor, byChinese=1)
                    HomeTeam = self.TeamNameCorrection(games[i+1].select('td.td-teaminfo div h3')[0].getText().strip(), cursor, byChinese=1)
                    # 取得先發
                    HomePitcher = games[i].select('td.td-teaminfo div p')[0].getText() if len(games[i].select('td.td-teaminfo div p'))>0 else ''
                    AwayPitcher = games[i+1].select('td.td-teaminfo div p')[0].getText() if len(games[i+1].select('td.td-teaminfo div p'))>0 else ''
                    if self.get_Alliance(HomeTeam, cursor) == self.TournamentText: #檢查是否為指定聯盟
                        # 轉換Bet365時間
                        MatchTime = self.MatchTimeCorrection(MatchTime.strftime("%Y-%m-%d %H:%M:%S.000"), 60, HomeTeam, AwayTeam, cursor)
                        # 取得EventCode
                        EventCode = games[i].select('td.td-gameinfo')[0].div.h3.getText().strip()
                        # 檢查是否有EventCode
                        if EventCode == '':
                            print('沒有EventCode')
                            continue
                        EventCode_Prefix = self.Games + '_' + MatchTime.strftime("%Y%m%d") + '_'  # 聯盟編號_比賽日期 ex. 2_20211213_
                        EventCode = EventCode_Prefix +EventCode
                        # 取得賠率
                        odds_html = [games[i].select("td[class^='td-bank-bet']"),games[i+1].select("td[class^='td-bank-bet']")]
                        # 整理
                        game_dict = dict(   SportText=self.SportText,
                                            TournamentText=self.TournamentText,
                                            HomeTeam=HomeTeam,
                                            AwayTeam=AwayTeam,
                                            Score='',
                                            MatchTime=MatchTime.strftime("%Y-%m-%d %H:%M:%S.000"),
                                            HomePitcher=HomePitcher,
                                            AwayPitcher=AwayPitcher,
                                            SourceCode=self.SourceCode,
                                            SportCode=self.SportCode,
                                            SportTournamentCode=self.SportTournamentCode,
                                            EventCode=EventCode,
                                            EventType=self.EventType,
                                            CollectClient=self.CollectClient,
                                            CollectedTime=self.CollectedTime,
                                            CreatedTime=datetime.now().astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S.000"),
                                            Odds_html=odds_html)

                        self.MatchEntry.append(game_dict)
                        print('爬取內容', game_dict)

        browser.close()
        browser.quit()
        cursor.close()
        db.close()

if __name__ == '__main__' :     
  MLBWebCrawler = MLBWebCrawler()
  print('MatchResultsSearchDays = [1天, 3天, 1週, 3週, 1月, 2月, 3月]')
  MLBWebCrawler.start(MatchResultsSearchDays='3天')