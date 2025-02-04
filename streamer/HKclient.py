import requests
from requests.auth import HTTPDigestAuth
from xml.dom.minidom import parse, parseString
import io, os, time
from datetime import datetime, timedelta
import pytz
import subprocess
import asyncio
import aioProc

#import xml.etree.ElementTree as ET
#from xml.etree.ElementTree import tostring
#from xml.etree.ElementTree import Element

import logging
import json
from datetime import datetime


LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


async def mergeVideo(count, snapID):
    #ffmpeg -f concat -i 文字檔檔名 -c copy 要輸出的影片檔檔名
    with open('videolist.txt', 'w') as f:
        for i in range(count):
            f.write('file ' + "'" + 'out' + snapID + '_' + str(i) + '.mp4' + "'" + '\n')
        f.close()
    
    command = 'ffmpeg -loglevel error -f concat -i videolist.txt -c copy ' + snapID + '.mp4'
    rtnErr = await aioProc.asyncRunWait(command)
    
    if os.path.isfile(snapID + '.mp4'):
        LOGGER.info('file len::%d', os.path.getsize(snapID + '.mp4'))
            


async def snapshot(camera, user, passwd, fileName):
    #host = '192.168.18.20'
    #userName = 'admin'
    #passWord = '1qazxsw2'
    
    url = 'http://'+ camera + '/ISAPI/Streaming/channels/101/picture'
    headers = {'Content-Type': 'application/xml'} 
    resp = requests.get(url, headers=headers, 
                        verify = False,
                        auth=HTTPDigestAuth(user, passwd),
                        timeout=60)
    #fileName = 'test.jpg'
    if resp.status_code == 200:
        with open(fileName, 'wb') as fd:
            for chunk in resp.iter_content(chunk_size=8192):
                fd.write(chunk)
    return resp.status_code

async def extractImage(index, timeCode, snapID):
    #ffmpeg -ss 00:01:00 -i input.mp4 -frames:v 1 output.png
    command = 'ffmpeg -loglevel error -i ' + index + '.mp4 -ss ' + timeCode + ' -frames:v 1 ' + snapID + '.jpg'
    rtnErr = await aioProc.asyncRunWait(command)
    
    #if os.path.isfile(snapID + '.jpg'):
    #    LOGGER.info('file len::%d', os.path.getsize(snapID + '.jpg'))
        
    return rtnErr

async def extractVideo(index, startTime, endTime):
    print(startTime, endTime)
    #ffmpeg -i input.mp4 -ss 00:00:05.000 -to 00:00:15.000 output.mp4
    command = 'ffmpeg -loglevel error -i ' + index + '.mp4 -ss ' + startTime + ' -to ' + endTime + ' out' + index + '.mp4'
    rtnErr = await aioProc.asyncRunWait(command)
    
    #if os.path.isfile('out' + index + '.mp4'):
    #    LOGGER.info('file len::%d', os.path.getsize('out' + index + '.mp4'))

    return rtnErr


async def downloadSD(camera, user, passwd, rtspStr, index):
    downloadXml = '''
                <downloadRequest version="1.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
                <playbackURI> </playbackURI>
                </downloadRequest>
                '''
    dom = parseString(downloadXml)
    collection = dom.documentElement
    playbackURI = collection.getElementsByTagName('playbackURI')
    playbackURI[0].childNodes[0].data = rtspStr
            
    strXml = io.StringIO()
    dom.writexml(strXml)
    outXml = strXml.getvalue()
    print(outXml)

    url = 'http://'+ camera + '/ISAPI/ContentMgmt/download'
    headers = {'Content-Type': 'application/xml'} 
    resp = requests.get(url, 
                        stream=True,
                        headers=headers, 
                        verify = False,
                        auth=HTTPDigestAuth(user, passwd),
                        data=outXml,
                        timeout=60)
    fileName = index + '.mp4' 
    
    if resp.status_code == 200:
        with open(fileName, 'wb') as fd:
            for chunk in resp.iter_content(chunk_size=8192):
                fd.write(chunk)

    return resp.status_code


async def querySD(camera, user, passwd, pullStart, pullEnd):
    print(pullStart)
    xmlData = '''<?xml version='1.0'?><CMSearchDescription>
            <searchID>C92DC285-8F30-0001-40C6-F0EFA8FB18B5</searchID>
            <trackList>
            <trackID>101</trackID></trackList>
            <timeSpanList>
            <timeSpan>
            <startTime> </startTime>
            <endTime> </endTime>
            </timeSpan>
            </timeSpanList>
            <maxResults>10</maxResults>
            <searchResultPostion>0</searchResultPostion>
            <metadataList>
            <metadataDescriptor>//recordType.meta.std-cgi.com</metadataDescriptor>
            </metadataList>
            </CMSearchDescription>
            '''
    
    doc = parseString(xmlData)
    collection = doc.documentElement
    startTime = collection.getElementsByTagName('startTime')
    startTime[0].childNodes[0].data = pullStart
    endTime = collection.getElementsByTagName('endTime')
    endTime[0].childNodes[0].data = pullEnd
    
    # Convert xml to python string
    out = io.StringIO()
    doc.writexml(out)
    outXml = out.getvalue()
    
    url = 'http://' + camera + '/ISAPI/ContentMgmt/search'
    headers = {'Content-Type': 'application/xml'} 
    resp = requests.get(url, headers=headers, 
                        verify = False,
                        auth=HTTPDigestAuth(user, passwd),
                        data=outXml,
                        timeout=60)
    if resp.status_code == 200:
        contentList = {}
        dom = parseString(resp.content)
        col = dom.documentElement
        match = int(col.getElementsByTagName('numOfMatches')[0].childNodes[0].data)
        for count in range(match):
            contentList[str(count)] = {}
            contentList[str(count)]['startTime'] = str(col.getElementsByTagName('startTime')[count].childNodes[0].data)
            contentList[str(count)]['endTime'] = str(col.getElementsByTagName('endTime')[count].childNodes[0].data)
            contentList[str(count)]['playbackURI'] = str(col.getElementsByTagName('playbackURI')[count].childNodes[0].data)
        return match, contentList


async def convertGMT(timeCode):
    localTime = datetime.strptime(timeCode, '%Y-%m-%d %H:%M:%S')
    localTZ = pytz.timezone('Asia/Taipei')
    gmtTime = localTZ.localize(localTime).astimezone(pytz.utc)
    return gmtTime.replace(tzinfo=None)
    
async def mapTimeCode(fileStart, fileEnd, pullStart, pullEnd):
    if fileStart <= pullStart:
        extractStart = pullStart
    else:
        extractStart = fileStart

    if fileEnd <= pullEnd:
        extractEnd = fileEnd
        #overFile = 1
    else:
        extractEnd = pullEnd
        #overFile = 0
            
    startDiff = extractStart - fileStart
    startMin = (startDiff.seconds // 60) % 60
    startSec = startDiff.seconds % 60
    
    endDiff = extractEnd - fileStart
    endMin = (endDiff.seconds // 60) % 60
    endSec = endDiff.seconds % 60
    return str(startMin) + ':' + str(startSec), str(endMin) + ':' + str(endSec)

async def extractFrame(camera, user, passwd, pullStart, snapID):
    pullTime = await convertGMT(pullStart)
    nativeStart = pullTime - timedelta(seconds=15)
    nativeEnd = pullTime + timedelta(seconds=15)

    count, queryList = await querySD(camera, user, passwd,
                    datetime.strftime(nativeStart, '%Y-%m-%dT%H:%M:%SZ'),
                    datetime.strftime(nativeEnd, '%Y-%m-%dT%H:%M:%SZ'))
    
    for i in range(count):
        print(i)
        fileStart = queryList[str(i)]['startTime']
        fileEnd = queryList[str(i)]['endTime']
        rtspUrl = queryList[str(i)]['playbackURI']
        tempID = snapID + '_' + str(i)
        rtn = await downloadSD(camera, user, passwd, rtspUrl, tempID)
        if rtn == 200:
            startTime = datetime.strptime(fileStart, '%Y-%m-%dT%H:%M:%SZ')
            endTime = datetime.strptime(fileEnd, '%Y-%m-%dT%H:%M:%SZ')
            beginTime, stopTime = await mapTimeCode(startTime, endTime, nativeStart, nativeEnd)
            err = await extractVideo(tempID, beginTime, stopTime)
            if pullTime >= startTime and pullTime <= endTime:
                beginTime, stopTime = await mapTimeCode(startTime, endTime, pullTime, pullTime)
                err = await extractImage(tempID, beginTime, snapID)
    if count > 1 :
        await mergeVideo(count, snapID)
    else:
        os.rename('out' + tempID + '.mp4', snapID + '.mp4')

    for i in range(count):
        if os.path.isfile(snapID + '_' + str(i) + '.mp4'):
            os.remove(snapID + '_' + str(i) + '.mp4')
        if os.path.isfile('out' + snapID + '_' + str(i) + '.mp4'):
            os.remove('out' + snapID + '_' + str(i) + '.mp4')
    if os.path.isfile('videolist.txt'):
        os.remove('videolist.txt')

    return count

#if __name__ == '__main__':
    #count = extractFrame('192.168.18.20', 'admin', '1qazxsw2', '2024-12-09 13:45:55', 'aaaa')
    #print(count)
    #snapshot()