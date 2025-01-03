import requests
from requests.auth import HTTPDigestAuth
from xml.dom.minidom import parse, parseString
import io, os, time
from datetime import datetime, timedelta
import pytz
import subprocess

#import xml.etree.ElementTree as ET
#from xml.etree.ElementTree import tostring
#from xml.etree.ElementTree import Element

import logging
import json
from datetime import datetime

def mergeVideo(count, snapID):
    #ffmpeg -f concat -i 文字檔檔名 -c copy 要輸出的影片檔檔名
    with open('videolist.txt', 'w') as f:
        for i in range(count):
            f.write('file ' + "'" + 'out' + str(i) + '.mp4' + "'" + '\n')
        f.close()
    command = ['ffmpeg', 
                '-loglevel', 'error',
                '-f', 'concat',
                '-i', 'videolist.txt',
                '-c', 'copy',
                snapID + '.mp4'
                ]
    print(command)
    process = subprocess.Popen(command, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True)
    
    stdOut, stdErr = process.communicate()
    if len(stdErr) != 0:
        print(stdErr)
        process.terminate()
        process.kill()
    return stdErr


def snapshot(camera, user, passwd, fileName):
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
            for chunk in resp.iter_content(chunk_size=2048):
                fd.write(chunk)
    return resp.status_code

def extractImage(index, timeCode, snapID):
    #ffmpeg -ss 00:01:00 -i input.mp4 -frames:v 1 output.png
    command = ['ffmpeg',
                '-loglevel', 'error',
                '-i', index + '.mp4',
                '-ss', timeCode,
                '-frames:v', '1',
                snapID + '.jpg']
    
    print('capture cmd::', command)
    process = subprocess.Popen(command, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True)
    
    stdOut, stdErr = process.communicate()
    print('stdErr:', stdErr)
    return stdErr

def extractVideo(index, startTime, endTime):
    print(startTime, endTime)
    #ffmpeg -i input.mp4 -ss 00:00:05.000 -to 00:00:15.000 output.mp4
    command = ['ffmpeg',
                '-loglevel', 'error',
                '-i', index + '.mp4',
                '-ss', startTime,
                '-to', endTime,
                'out' + index + '.mp4']
    
    print('capture cmd::', command)
    process = subprocess.Popen(command, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True)
    
    stdOut, stdErr = process.communicate()
    if len(stdErr) != 0:
        if os.path.isfile('out' + index + '.mp4'):
            os.remove('out' + index + '.mp4')
        process.terminate()
        process.kill()
    return stdErr

def downloadSD(camera, user, passwd, rtspStr, index):
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
    resp = requests.get(url, headers=headers, 
                        verify = False,
                        auth=HTTPDigestAuth(user, passwd),
                        data=outXml,
                        timeout=60)
    fileName = index + '.mp4' 
    if resp.status_code == 200:
        with open(fileName, 'wb') as fd:
            for chunk in resp.iter_content(chunk_size=10240):
                fd.write(chunk)
                #time.sleep(0.5)
            #df.close
    return resp.status_code


def querySD(camera, user, passwd, pullStart, pullEnd):
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


def convertGMT(timeCode):
    localTime = datetime.strptime(timeCode, '%Y-%m-%d %H:%M:%S')
    localTZ = pytz.timezone('Asia/Taipei')
    gmtTime = localTZ.localize(localTime).astimezone(pytz.utc)
    return gmtTime.replace(tzinfo=None)
    
def mapTimeCode(fileStart, fileEnd, pullStart, pullEnd):
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

def extractFrame(camera, user, passwd, pullStart, snapID):
    pullTime = convertGMT(pullStart)
    nativeStart = pullTime - timedelta(seconds=15)
    nativeEnd = pullTime + timedelta(seconds=15)

    count, queryList = querySD(camera, user, passwd,
                    datetime.strftime(nativeStart, '%Y-%m-%dT%H:%M:%SZ'),
                    datetime.strftime(nativeEnd, '%Y-%m-%dT%H:%M:%SZ'))
    
    for i in range(count):
        print(i)
        fileStart = queryList[str(i)]['startTime']
        fileEnd = queryList[str(i)]['endTime']
        rtspUrl = queryList[str(i)]['playbackURI']
        
        rtn = downloadSD(camera, user, passwd, rtspUrl, str(i))
        if rtn == 200:
            startTime = datetime.strptime(fileStart, '%Y-%m-%dT%H:%M:%SZ')
            endTime = datetime.strptime(fileEnd, '%Y-%m-%dT%H:%M:%SZ')
            beginTime, stopTime = mapTimeCode(startTime, endTime, nativeStart, nativeEnd)
            err = extractVideo(str(i), beginTime, stopTime)
            print(err)            
            if pullTime >= startTime and pullTime <= endTime:
                beginTime, stopTime = mapTimeCode(startTime, endTime, pullTime, pullTime)
                err = extractImage(str(i), beginTime, snapID)
    if count > 1 :
        mergeVideo(count, snapID)
    else:
        os.rename('out0.mp4', snapID + '.mp4')

    for i in range(count):
        os.remove(str(i) + '.mp4')
        os.remove('out' + str(i) + '.mp4')
    os.remove('videolist.txt')

    return count

#if __name__ == '__main__':
    #count = extractFrame('192.168.18.20', 'admin', '1qazxsw2', '2024-12-09 13:45:55', 'aaaa')
    #print(count)
    #snapshot()