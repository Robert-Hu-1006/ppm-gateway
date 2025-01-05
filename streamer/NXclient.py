import asyncio
import aiohttp
import logging
import json
import aiofiles
from datetime import datetime, timedelta

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

async def getNXstatus(nvr, camID, port, user, passwd):
    auth = aiohttp.BasicAuth(login=user, password=passwd)
    conn = aiohttp.TCPConnector(verify_ssl=False)

    async with aiohttp.ClientSession(connector=conn,auth=auth) as session:
        statusURL = 'https://' + nvr + ':' + port + '/ec2/getStatusList?id=' + camID
        async with await session.get(statusURL) as statusResp:
                if statusResp.status == 200:
                    data = await statusResp.json()
                    LOGGER.info('camera status:: %s', data[0]['status'] )
                    if data[0]['status'] == 'Recording':
                        return True
                    else:
                        return False


async def getNXcontent(nvr, camID, port, user, passwd, snapID, timestamp):
    auth = aiohttp.BasicAuth(login=user, password=passwd)
    conn = aiohttp.TCPConnector(verify_ssl=False)

    async with aiohttp.ClientSession(connector=conn,auth=auth) as session:
        # get snapshot
        imageURL = 'https://' + nvr +':' + port + '/ec2/cameraThumbnail?cameraId=' + camID + '&time=' + timestamp
        async with await session.get(imageURL) as imgResp:
            if imgResp.status == 200:
                imgFile = '/app/' + snapID + '.jpg'
                data = await imgResp.read()
                with open(imgFile, "wb") as f1: 
                    f1.write(data)
                    f1.close()
                        
        # Get Video Clips
        start = datetime.fromisoformat(timestamp) + timedelta(seconds=-15)
        stamp = start.isoformat(timespec='seconds')
        videoURL = 'https://' + nvr +':' + port + '/media/' + camID + '.mp4?pos=' + stamp + '&duration=30'
    
        # Delay 15 sec
        await asyncio.sleep(1) 
        mb = 1024 * 1024
        async with await session.get(videoURL) as videoResp:
            if videoResp.status == 200:
                videoFile = '/app/' + snapID + '.mp4'
                async with aiofiles.open(videoFile,"wb") as f2:
                    while True:
                        chunk=await videoResp.content.read(mb)
                        if not chunk:
                            break
                        await f2.write(chunk)
                        await asyncio.sleep(0)


async def getNXsnapshot(nvr, camID, port, user, passwd, snapID):
    auth = aiohttp.BasicAuth(login=user, password=passwd)
    conn = aiohttp.TCPConnector(verify_ssl=False)

    async with aiohttp.ClientSession(connector=conn,auth=auth) as session:
        try:
            # check camera status
            url = 'https://'  + nvr + ':' + port + '/rest/v2/devices/' + camID + '/image'
            #url = 'http://' + nvr + ':'+ port +'/ec2/cameraThumbnail?cameraId=' + camID  # &time=2020-05-22T12:00:00.000
            async with await session.get(url) as resp:
                if resp.status == 200:
                    #if not os.path.isdir(FOLDER):
                    #    os.mkdir(FOLDER)
                        
                    imgFile = '/app/' + snapID + '.jpg'
                    data = await resp.read()
                    with open(imgFile, "wb") as f: 
                        f.write(data)
                        f.close()  
            return resp.status              
        except aiohttp.ClientPayloadError:
            LOGGER.info('ClientPayloadError::')
            await session.close()


#if __name__ == '__main__':
#    timestamp = datetime.strftime(datetime.now(), '%Y-%m-%dT%H:%M:%SZ')
#    timeObj = datetime.strptime('2025-01-03 09:10:15', '%Y-%m-%d %H:%M:%S')
#    timeStr = datetime.strftime(timeObj, '%Y-%m-%dT%H:%M:%SZ')
    #asyncio.run(getNXcontent('103.241.166.150','0dcda699-794f-8d8f-34f5-cce4cccef218','7011','admin','n39501022x','aaaa', timestamp))
    #asyncio.run(getNXsnapshot('192.168.18.7','bbf6e391-beb5-828a-64f7-86677fb65430','7001','admin','Az123567','aaaa'))
    