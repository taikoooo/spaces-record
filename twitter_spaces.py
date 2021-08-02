# -*- coding: utf-8 -*-

import requests
import os
import json
import datetime
import time
import traceback
import re
import threading
import csv
from itertools import islice

class twitter_spaces:
    def __init__(self, setDict):
        '''
        key           |  描述
        :-----------  | :----------
        space_id      |  spaces的rest_id
        save_path     |  同主程序
        headers       |  主程序生成
        cookie        |  同主程序
        times_aac_err |  同主程序
        '''
        # 配置文件初始化
        self.spaceId = setDict['space_id']
        self.savePath = setDict['save_path']
        self.headers = setDict['headers']
        self.cookie = setDict['cookie']
        self.timesAacErr = setDict['times_aac_err']

        # 通用数据初始化
        self.metaDict = {}
        self.m3uList = []
        self.rootPath = None

    def get_media_key(self):
        '''
        通过spaces的restid获取media_key，注意不是用户restid，而是spaces的restid，即spaces链接的最后一段
        '''
        variables = {"id":self.spaceId,"withNonLegacyCard":False,"withTweetResult":False,"withReactions":False,"withSuperFollowsTweetFields":False,"withUserResults":False,"withBirdwatchPivots":False,"withScheduledSpaces":False}
        params = (('variables', json.dumps(variables, ensure_ascii=False)),)
        
        while 1:
            try:
                response = requests.get('https://twitter.com/i/api/graphql/wUwS7TMgSm0Po-Gg-Q2h9w/AudioSpaceById', headers=self.headers, params=params, cookies=self.cookie)
                response.raise_for_status()
                self.metaDict = response.json()['data']['audioSpace']['metadata']
                print(self.metaDict)
                
                # 在存储路径内创建当前spaces的存储根文件夹，内部正常应包含info.json(spaces信息文件)、rec.aac(录像)、rec.log(录像写入日志，csv格式)
                self.rootPath = os.path.join(self.savePath, '{created_at}_{rest_id}'.format(**self.metaDict))
                if not os.path.exists(self.rootPath):
                    os.makedirs(self.rootPath)
                
                # 记录get_media_key和get_url获取的信息
                with open(os.path.join(self.rootPath, 'info.json'), 'w', encoding='utf-8') as f:
                    json.dump(self.metaDict, f, ensure_ascii=False, indent=4)
                
                if self.metaDict['state'] in ['TimedOut','Ended']:
                    print('{created_at}_{rest_id} info threading ended'.format(**self.metaDict))
                    return
                elif self.metaDict['state'] == 'Running':
                    time.sleep(300)
                else:
                    time.sleep(10)

            except Exception:
                print('{time} get_media_key({id}) {info}'.format(
                    time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'), 
                    id = self.spaceId, info = {'info': traceback.format_exc()}
                ))
                time.sleep(3)

    def __get_url(self, mediaKey):
        '''
        通过get_media_key得到的mediaKey，获取spaces的m3u8文件下载链接
        '''
        # 返回值初始化
        streamDict = {
            'status': '',
            'stream_type': '',
            'session_id': '',
            'url': '',
            'chat_permission_type': ''
        }

        params = (
            ('client', 'web'),
            ('use_syndication_guest_id', 'false'),
            ('cookie_set_host', 'twitter.com'),
        )

        try:
            response = requests.get('https://twitter.com/i/api/1.1/live_video_stream/status/{}'.format(mediaKey), headers=self.headers, params=params, cookies=self.cookie)
            response.raise_for_status()
            streamDict['status'] = response.json()['source']['status']
            streamDict['stream_type'] = response.json()['source']['streamType']
            streamDict['session_id'] = response.json()['sessionId']
            streamDict['url'] = response.json()['source']['location']
            streamDict['chat_permission_type'] = response.json()['chatPermissionType']

            return streamDict
        except Exception:
            return traceback.format_exc()

    def get_m3u(self, url):
        '''
        下载m3u8文件
        '''
        while 1:
            try:
                response = requests.get(url)
                response.raise_for_status()
                for line in response.text.split('\n'):
                    if line[0:1] != '#' and line not in self.m3uList:
                        self.m3uList.append(line)
                time.sleep(3)
            except Exception:
                print('{time} get_m3u({id}) {info}'.format(
                    time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'), 
                    id = self.spaceId, info = {'info': traceback.format_exc()}
                ))
                if 'Not Found for url' in traceback.format_exc():
                    print('{created_at}_{rest_id} get_m3u threading ended'.format(**self.metaDict))
                    return
                time.sleep(1)
            
    def __get_aac(self, url):
        '''
        下载aac文件
        '''
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.content
        except Exception:
            return traceback.format_exc()

    def run(self):
        '''
        录制程序主体
        '''
        while 1:
            if self.rootPath:
                break
            time.sleep(0.1)

        if self.metaDict['state'] in ['TimedOut','Ended']:
            print('{created_at}_{rest_id} download threading ended'.format(**self.metaDict))
            return
        
        # 获取m3u8文件下载链接
        while 1:
            streamDict = self.__get_url(self.metaDict['media_key'])
            if isinstance(streamDict, dict):
                break
            
            print('{time} __get_url({id}) {info}'.format(
                time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'), 
                id = self.spaceId, info = {'info': traceback.format_exc()}
            ))
            time.sleep(3)
        
        # 提取和调整m3u8下载链接
        mUrl = streamDict['url']
        dirUrl = mUrl.replace('dynamic_playlist.m3u8?type=live','')

        # 获取m3u8文件
        m3uTh = threading.Thread(target=self.get_m3u, args=(mUrl,), daemon=True)
        m3uTh.start()

        # 录制文件和日志文件初始化
        if 'rec.log' not in os.listdir(self.rootPath):
            with open(os.path.join(self.rootPath, 'rec.log'), 'w', encoding='utf-8-sig', newline='') as f:
                csv.writer(f).writerow(['chunkTs', 'chunkNo', 'startSize', 'chunkSize'])
        if 'rec.aac' not in os.listdir(self.rootPath):
            with open(os.path.join(self.rootPath, 'rec.aac'), 'wb') as f:
                f.write(bytes())
        
        # 用于记录已下载的chunk，防止重复
        overList = []

        # 读取日志文件，用于中断程序后恢复
        with open(os.path.join(self.rootPath, 'rec.log'), 'r', encoding='utf-8-sig', newline='') as f:
            for row in islice(csv.reader(f), 1, None):
                overList.append('chunk_{0}_{1}_a.aac?type=live'.format(*row))
        
        while 1:
            # 读取m3u8
            for line in self.m3uList[:]:
                # 防重复
                if line in overList:
                    self.m3uList.remove(line)
                    continue

                # 当行内容不符合格式时跳过
                if not re.search('chunk_[0-9]*_[0-9]*_.*', line):
                    continue
                
                chunkTs = line.split('_')[1]
                chunkNo = line.split('_')[2]
                
                # 重试，超时则跳过
                for i in range(self.timesAacErr):
                    accData = self.__get_aac('{0}{1}'.format(dirUrl, line))
                    if isinstance(accData, str):
                        print('{time} {chunkTs} {chunkNo:>4} Failed({times})'.format(
                            time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                            chunkTs = chunkTs, chunkNo = chunkNo, times = i + 1))
                        time.sleep(1)
                    else:
                        startSize = os.path.getsize(os.path.join(self.rootPath, 'rec.aac'))
                        with open(os.path.join(self.rootPath, 'rec.aac'), 'ab') as f: chunkSize = f.write(accData)
                        chunkInfo = [chunkTs, chunkNo, startSize, chunkSize]
                        with open(os.path.join(self.rootPath, 'rec.log'), 'a', encoding='utf-8-sig', newline='') as f:
                            csv.writer(f).writerow(chunkInfo)
                        overList.append(line)
                        self.m3uList.remove(line)
                        print('{time} {0} {1:>4} Successful, startSize: {2:>9}, chunkSize: {3:>5}'.format(
                            time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'), *chunkInfo))
                        break
                time.sleep(1)

            if self.metaDict['state'] in ['TimedOut','Ended'] and not m3uTh.is_alive():
                print('{created_at}_{rest_id} download threading ended'.format(**self.metaDict))
                return
            time.sleep(1)

def get_mainjs():
    headers = {
        'Origin': 'https://twitter.com',
        'Referer': 'https://twitter.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.115 Safari/537.36',
    }

    response = requests.get('https://abs.twimg.com/responsive-web/client-web/main.1ad07545.js', headers=headers)
    response.raise_for_status()
    
    queryList = re.findall('queryId:"([^"]*)",operationName:"([^"]*)",operationType:"([^"]*)"', response.text)
    queryDict = {i[1]:{'id':i[0],'type':i[2]} for i in queryList}

    return queryDict

def twitter_twitlist(setDict):
    variables = {"userId":setDict['rest_id'],"count":20,"withHighlightedLabel":True,"withTweetQuoteCount":True,"includePromotedContent":True,"withTweetResult":True,"withReactions":False,"withSuperFollowsTweetFields":False,"withSuperFollowsUserFields":False,"withUserResults":False,"withVoice":True,"withNonLegacyCard":False,"withBirdwatchPivots":False}
    params = (('variables', json.dumps(variables ,ensure_ascii=False)),)

    response = requests.get('https://twitter.com/i/api/graphql/{}/UserTweets'.format(get_mainjs()['UserTweets']['id']), headers=setDict['headers'], params=params, cookies=setDict['cookie'])
    response.raise_for_status()
    # 通过正则提取spaces链接
    return re.findall('twitter.com/i/spaces/([0-9|a-z|A-Z]{13})', response.text)

def main(setDict):
    '''
    key           | required |  描述
    :-------      | :------: |  :----
    user_id       |     N    |  用户rest_id，注意不是screen_name，默认为用户kaguramea_vov的id
    save_path     |     N    |  文件存储路径，默认为主程序文件夹下的"./rec/{user_id}"
    cookie        |     Y    |  账号cookie，因推特必须登录使用，无cookie无法运行（未设置防错）
    invl_twit     |     N    |  获取推文间隔，单位为秒，默认60
    invl_twit_err |     N    |  获取推文失败时，重试间隔，单位为秒，默认10
    times_aac_err |     N    |  获取aac片段失败时，最大重试次数，不建议太多，以防止错过后面的片段，默认5
    '''
    # 运行参数初始化
    userId = setDict.get('user_id', '1130858667547299841')
    savePath = setDict.get('save_path', './rec/{}'.format(userId))
    cookie = setDict['cookie']
    headers = {
        'x-csrf-token': setDict['cookie']['ct0'],
        'Origin': 'https://twitter.com',
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36',
    }
    invlTwit = setDict.get('invl_twit', 60)
    invlTwitErr = setDict.get('invl_twit_err', 10)
    timesAacErr = setDict.get('times_aac_err', 5)

    # 捕获spaces链接时使用，将获取的rest_id记录为数组，以防止重复开启录制线程
    spacesList = []
    while 1:
        try:
            reFind = twitter_twitlist({'rest_id':userId, 'headers':headers, 'cookie':cookie})
            for spaceId in set(reFind):
                if spaceId not in spacesList:
                    spacesList.append(spaceId)
                    emp = twitter_spaces({'space_id': spaceId, 'save_path': savePath, 'headers': headers, 'cookie': cookie, 'times_aac_err': timesAacErr})
                    infoTh = threading.Thread(target=emp.get_media_key, daemon=True)
                    infoTh.start()
                    mainTh = threading.Thread(target=emp.run, daemon=True)
                    mainTh.start()
            
            # 循环间隔不建议太低
            time.sleep(invlTwit)

        except Exception:
            print('{time} main {info}'.format(
                time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'), 
                info = {'info': traceback.format_exc()}
            ))
            time.sleep(invlTwitErr)
            

if __name__ == '__main__':
    os.chdir(os.path.abspath(os.path.dirname(__file__)))

    if 'twitter_spaces.json' in os.listdir('./'):
        with open('twitter_spaces.json', 'r', encoding='utf-8') as f:
            setDict = json.load(f)
    else:
        print('无配置文件')

    main(setDict)