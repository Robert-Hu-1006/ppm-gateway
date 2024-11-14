import pygsheets
import logging
import subprocess
import psutil
import signal
import os 
import json
import asyncio
import aiomqtt
import aiohttp
import configparser
#import ssl
from dotenv import load_dotenv

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

MQTT_POOL = None
LICENSE = None
CAM_TABLE = {}
class Stream:
    def __init__(self, pid, name):
        self.pid = pid
        self.name = name

async def copyTag(key, row):
    sensorTable ={}
    sensorTable[key] = {}
    sensorTable[key]['org'] =  row[0]
    sensorTable[key]['code'] =  row[1]
    sensorTable[key]['deviceName'] =  row[4]
    sensorTable[key]['sensorType'] =  row[6]
    sensorTable[key]['alarmGroup'] =  row[7]
    sensorTable[key]['alarmType'] =  row[8]
    sensorTable[key]['floor'] =  row[10]
    sensorTable[key]['area'] =  row[11]
    sensorTable[key]['alarmPriority'] =  row[12]
    sensorTable[key]['sop'] =  row[13]
    sensorTable[key]['source'] =  row[14]
    if row[15] == '':
        camLink = 'na'
    else:
        camLink = row[13]
    sensorTable[key]['cam_link'] =  camLink
    return sensorTable

async def genTelegrafTag():
    client = pygsheets.authorize(service_account_file='/app/service.json')
    #client = pygsheets.authorize(service_account_file='./streamer/client_secret.json')
    sheet = client.open_by_key(LICENSE['sheet'])
    #sheet = client.open_by_key('1YjsaWo06B6p02qZfL2sL6N87o3bndwEDa3yCFWQY_QA')

    ppm_tag = '/etc/telegraf/tag/ppm_tag.json'
    #ppm_tag = './streamer/ppm_tag.json'
    sensorTable = {}
    
    if os.path.isfile(ppm_tag):
        os.remove(ppm_tag)
    wrkSheet = sheet.worksheet_by_title('Sensor')
    gTable = wrkSheet.get_values('A2', 'P')
    for i in range(len(gTable) - 1):
        deviceID = gTable[i + 1][3].lower()
        dataChannel = gTable[i + 1][9].lower()
        key = deviceID + '_' + dataChannel
        sensorTable[key] = {}
        sensorTable[key]['org'] =  gTable[i + 1][0]
        sensorTable[key]['code'] =  gTable[i + 1][1]
        sensorTable[key]['deviceName'] =  gTable[i + 1][4]
        sensorTable[key]['sensorType'] =  gTable[i + 1][6]
        sensorTable[key]['alarmGroup'] =  gTable[i + 1][7]
        sensorTable[key]['alarmType'] =  gTable[i + 1][8]
        sensorTable[key]['floor'] =  gTable[i + 1][10]
        sensorTable[key]['area'] =  gTable[i + 1][11]
        sensorTable[key]['alarmPriority'] =  gTable[i + 1][12]
        sensorTable[key]['sop'] =  gTable[i + 1][13]
        sensorTable[key]['source'] =  gTable[i + 1][14]
        if gTable[i + 1][15] == '':
            camLink = 'na'
        else:
            camLink = gTable[i + 1][13]
            sensorTable[key]['cam_link'] =  camLink
        
    with open(ppm_tag, 'w') as SensorFile:
        json.dump(sensorTable, SensorFile, indent=2)
    SensorFile.close


async def killProcess(pid):
    process = psutil.Process(pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()
    #os.killpg(pid, signal.SIGUSR1)

async def picUpload(fileName):
    uploadURL = 'https://' + os.getenv('PPM_CLOUD') + '/api/ppm/stream/snapshot' 
    headers = { "Authorization": "Bearer " + os.getenv('API_TOKEN')}
    formData = aiohttp.FormData()
    file = open('/app/' + fileName, 'rb')
    formData.add_field('org', os.getenv('PPM_ORG'))
    formData.add_field('code', os.getenv('PPM_PCODE'))
    formData.add_field('file', open('/app/' + fileName, 'rb'), filename=fileName)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(uploadURL, 
                                    headers=headers, 
                                    ssl=False, 
                                    data=formData) as response:
                return response.status
        except aiohttp.ClientConnectorError as e:
          LOGGER.info('Connection Error::%s', str(e))

async def captureFrame(pullURL, fileName):
    #ffmpeg -rtsp_transport tcp -i rtsp://admin:Az123567@192.168.18.7:7001/e3e9a385-7fe0-3ba5-5482-a86cde7faf48 -frames:v 1 -q:v 1 -f image2 /app/test_image.jpg
    command = ['ffmpeg',
                '-loglevel', 'error',
                '-rtsp_transport', 'tcp',
                '-i', pullURL,
                '-frames:v', '1',
                '-q:v', '1',
                '-f', 'image2', '/app/' + fileName]
    
    LOGGER.info('capture cmd::%s', command)
    process = subprocess.Popen(command, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True)
    
    stdOut, stdErr = process.communicate()
    LOGGER.info('stdErr: %s', type(stdErr))
    if len(stdErr) == 0:
        if os.path.isfile('/app/' + fileName):
            rtn = await picUpload(fileName)
            if rtn == 200:
                os.remove('/app/' + fileName)
    else:
        LOGGER.info('time out error')
        process.terminate()
        process.kill()

async def pushStream( pull_url, push_url):
    #convert RTSP H265 (hevc) stream to H264
    #ffmpeg -i rtsp://admin:Az123567@192.168.18.7:7001/e3e9a385-7fe0-3ba5-5482-a86cde7faf48 -map 0:v:0 -c:v libx264 -preset ultrafast -b:v 500k -max_muxing_queue_size 1024 -f rtsp rtsp://robertcloud.net:8554/live/0/Savills/2F_Office
    #ffmpeg -fflags +genpts -rtsp_transport tcp  -i rtsp://admin:Az123567@192.168.18.7:7001/e3e9a385-7fe0-3ba5-5482-a86cde7faf48 -c copy -f rtsp -preset ultrafast rtsp://robertcloud.net:8554/live/0/Savills/2F_Office
    #ffmpeg -fflags +genpts -rtsp_transport tcp -i rtsp://192.168.18.7/gamamia02.avi -c:v libx264 -f rtsp -preset ultrafast rtsp://robertcloud.net:8554/live/0/Savills/2F_Office

    #-loglevel error
    command = ['ffmpeg',
                '-fflags', '+genpts',
                '-rtsp_transport', 'tcp',
                '-i', pull_url,
                '-c', 'copy',
                '-f', 'rtsp',
                '-preset', 'ultrafast',
                push_url]
    
    #process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    LOGGER.info('cmd::%s', command)
    process = subprocess.Popen(command, 
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True)
                    
    if process.returncode is None:
        rtnPID = process.pid
    else:
        rtnPID = 0
        process.terminate()
        process.kill()
        LOGGER.info('error::%s', str(process.returncode))
    return rtnPID
   
async def loadPingTable(sheet):
    pingTable = {}
    wrkSheet = sheet.worksheet_by_title('Sensor')
    gSheet = wrkSheet.get_values('A2', 'P')
    config = configparser.ConfigParser(strict=False)
    # 保留原先鍵大小寫
    config.optionxform = lambda option: option
    
    pCode = os.getenv('PPM_PCODE')
    ipList = []
    if os.path.isfile('/etc/telegraf/conf/ping.conf'):
        os.remove('/etc/telegraf/conf/ping.conf')
    #if os.path.isfile('./streamer/ping.conf'):
    #    os.remove('./streamer/ping.conf')
    LOGGER.info('sensor len:%s', str(len(gSheet)))
    
    for i in range(len(gSheet)-1):
        if gSheet[i + 1][1] == pCode: 
            ip = gSheet[i + 1][4]
            if ip not in ipList:
                config['[inputs.ping]'] = {}
                ipList.append(ip)
                config['[inputs.ping]']['urls'] = '["' + gSheet[i + 1][5] + '"]'
                config['[inputs.ping]']['method'] = '"exec"'
                config['[inputs.ping]']['count'] = '3'
                config['[inputs.ping]']['interval'] = '"60s"'
                config['[inputs.ping]']['timeout'] = '3.0'

                config['inputs.ping.tags'] = {}
                config['inputs.ping.tags']['deviceID'] = '"' + gSheet[i + 1][3].lower() + '"'
                config['inputs.ping.tags']['deviceName'] = '"' + gSheet[i + 1][4] + '"'
                config['inputs.ping.tags']['sensorType'] = '"' + gSheet[i + 1][6] + '"'
                config['inputs.ping.tags']['alarmGroup'] = '"IP_Device"'
                config['inputs.ping.tags']['alarmType'] = '"Device_Disconnect"'
                config['inputs.ping.tags']['floor'] = '"' + gSheet[i + 1][10] + '"'
                config['inputs.ping.tags']['area'] = '"' + gSheet[i + 1][11] + '"'
                config['inputs.ping.tags']['alarmPriority'] = '"Critical"'
                config['inputs.ping.tags']['sop'] = '"9"'
                config['inputs.ping.tags']['source'] = '"' + gSheet[i + 1][14] + '"'
                if gSheet[i + 1][15] == '':
                    config['inputs.ping.tags']['camLink'] = '"na"'
                else:
                    config['inputs.ping.tags']['camLink'] = '"' + gSheet[i + 1][15] + '"'
            with open('/etc/telegraf/conf/ping.conf', 'a') as configfile:
            #with open('./streamer/ping.conf', 'a') as configfile:
                config.write(configfile)
                #config = configparser.ConfigParser(strict=False)
            configfile.close

    wrkSheet = sheet.worksheet_by_title('LiveCam')
    gSheet = wrkSheet.get_values('A2', 'K')
    LOGGER.info('livecam len:%s', str(len(gSheet)))
    for j in range(len(gSheet)-1):
        if gSheet[j + 1][1] == pCode: 
            ip = gSheet[j + 1][8]
            if ip not in ipList and ip != '':
                config['[inputs.ping]'] = {}
                ipList.append(ip)
                config['[inputs.ping]']['urls'] = '["' + gSheet[j + 1][8] + '"]'
                config['[inputs.ping]']['method'] = '"exec"'
                config['[inputs.ping]']['count'] = '3'
                config['[inputs.ping]']['interval'] = '"60s"'
                config['[inputs.ping]']['timeout'] = '3.0'

                config['inputs.ping.tags']['deviceID'] = '"' + gSheet[j + 1][3].lower() + '"'
                config['inputs.ping.tags']['deviceName'] = '"' + gSheet[j + 1][4] + '"'
                config['inputs.ping.tags']['sensorType'] = '"CAM"'
                config['inputs.ping.tags']['alarmGroup'] = '"IP_Device"'
                config['inputs.ping.tags']['alarmType'] = '"Device_Disconnect"'
                config['inputs.ping.tags']['floor'] = '"' + gSheet[j + 1][6] + '"'
                config['inputs.ping.tags']['area'] = '"' + gSheet[j + 1][7] + '"'
                config['inputs.ping.tags']['alarmPriority'] = '"Critical"'
                config['inputs.ping.tags']['sop'] = '"9"'
                config['inputs.ping.tags']['source'] = '""'
                config['inputs.ping.tags']['camLink'] = '"' + gSheet[j + 1][4] + '"'
    
            with open('/etc/telegraf/conf/ping.conf', 'a') as configfile:
            # with open('./streamer/ping.conf', 'a') as configfile:
                config.write(configfile)
                #config = configparser.ConfigParser(strict=False)
            configfile.close    
    
async def loadCamTable(wrkSheet):
    camTable = {}
    pCode = os.getenv('PPM_PCODE')
    gSheet = wrkSheet.get_values('A2', 'N')
    for i in range(len(gSheet) - 1):
        if gSheet[i + 1][1] == pCode:
            name = gSheet[i + 1][4]
            camTable[name] = {}
            camTable[name]['code'] =  gSheet[i + 1][1]
            camTable[name]['source'] =  gSheet[i + 1][2]
            camTable[name]['camID'] =  gSheet[i + 1][3]
            camTable[name]['path'] =  gSheet[i + 1][5]
            camTable[name]['floor'] =  gSheet[i + 1][6]
            camTable[name]['area'] =  gSheet[i + 1][7]
            camTable[name]['ip'] =  gSheet[i + 1][8]
            camTable[name]['port'] =  gSheet[i + 1][9]
            camTable[name]['account'] =  gSheet[i + 1][10]
            camTable[name]['passwd'] =  gSheet[i + 1][11]
            camTable[name]['token'] =  gSheet[i + 1][12]

    if os.path.isfile('/app/camTable.json'):
        os.remove('/app/camTable.json')

    with open('/app/camTable.json', 'w', encoding='utf8') as camFile:
        json.dump(camTable, camFile, ensure_ascii=False, indent=2)
    camFile.close
    return i, camTable

async def configTables():
    global CAM_TABLE
    try:
        client = pygsheets.authorize(service_account_file='/app/service.json')
        #client = pygsheets.authorize(service_account_file='/app/client_secret.json')
        sheet = client.open_by_key(LICENSE['sheet'])
        
        # reload camera table from google sheet
        wrkSheet = sheet.worksheet_by_title('LiveCam')
        count, CAM_TABLE = await loadCamTable(wrkSheet)
        if count == 0:
            CAM_TABLE = json.load(open('/app/camTable.json','r'))

        # reload ping table from google sheet for telegraf
        await loadPingTable(sheet)

    except Exception as e:
        LOGGER.info('Read Google Sheet Error :: %s', str(e))


async def downloadGoogleKey():
    downloadURL = 'https://' + os.getenv('PPM_CLOUD') + \
                        '/api/ppm/license/download?org=' + \
                        os.getenv('PPM_ORG') + \
                        '&code=' + os.getenv('PPM_PCODE')
    headers = {
            "accept": "application/json",
            "Authorization": "Bearer " + os.getenv('API_TOKEN')
        }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(downloadURL, headers=headers, ssl=False) as response:
                if response.status == 200:
                    keyRtn = await response.json()
                    ##await response.read()
                    with open('/app/service.json', 'w') as keyFile:
                        json.dump(keyRtn, keyFile, indent=2)
                    keyFile.close 
                    return response.status 
        except aiohttp.ClientConnectorError as e:
          LOGGER.info('Connection Error::%s', str(e))
    
async def getLicenseInfo():
    queryURL = 'https://' + os.getenv('PPM_CLOUD') + '/api/ppm/license/query?org=' + os.getenv('PPM_ORG')
    headers = { "Authorization": "Bearer " + os.getenv('API_TOKEN')}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(queryURL, headers=headers, ssl=False) as response:
                if response.status == 200:
                    licRtn = await response.json()
                    return licRtn 
        except aiohttp.ClientConnectorError as e:
          LOGGER.info('Connection Error::%s', str(e))


async def buildCommand(streamType, camName):
    match CAM_TABLE[camName]['source']:
        case 'NX_MERGE':
            pullURL = 'rtsp://' + CAM_TABLE[camName]['ip'] + ':' + \
                                CAM_TABLE[camName]['port'] + '/' + \
                                CAM_TABLE[camName]['camID'] + '?lo&auth=' + \
                                CAM_TABLE[camName]['token']
        case 'NX_NVR':
            pullURL = 'rtsp://' + CAM_TABLE[camName]['account'] + ':' + \
                                CAM_TABLE[camName]['passwd'] + '@' + \
                                CAM_TABLE[camName]['ip'] + ':' + \
                                CAM_TABLE[camName]['port'] + '/' + \
                                CAM_TABLE[camName]['camID']
        case 'SIM_CAM':
            pullURL = 'rtsp://' + CAM_TABLE[camName]['ip'] + '/' + \
                                CAM_TABLE[camName]['camID']
        case '_':
            pullURL = 'rtsp://' + CAM_TABLE[camName]['account'] + ':' + \
                                CAM_TABLE[camName]['passwd'] + '@' + \
                                CAM_TABLE[camName]['ip'] + ':' + \
                                CAM_TABLE[camName]['port'] + '/' + \
                                CAM_TABLE[camName]['camID']

    pushURL = 'rtsp://' + os.getenv('PPM_CLOUD') + ':8554/live/' + \
            streamType + '/' + \
            os.getenv('PPM_ORG') + '/' + \
            camName
    LOGGER.info('pull: %s push: %s', pullURL, pushURL)
    return pullURL, pushURL

async def main():
    global LICENSE
    LICENSE = await getLicenseInfo()
    if (LICENSE is not None) and ('expire' in LICENSE.keys()):
        with open('/data/lic.json', 'w', encoding='utf8') as licFile:
            json.dump(LICENSE, licFile, ensure_ascii=False, indent=2)
        licFile.close
    #if 'expire' in LICENSE.keys():
        LOGGER.info('license expire date:%s', LICENSE['expire'])
        
        await downloadGoogleKey()
        await configTables()
        await genTelegrafTag()

        client = aiomqtt.Client(
                        hostname=os.getenv('PPM_CLOUD'),
                        port=1888,
                        username=os.getenv('MQTT_USR'),
                        password=os.getenv('MQTT_PWD'),
                        identifier = os.getenv('PPM_ORG') + '_' + os.getenv('PPM_PCODE'), 
                        clean_session = True,
                        timeout=10,
                        keepalive=10
                        )
        LOGGER.info('Connect MQTT Broker :%s', str(client))
        interval = 3  # Seconds
        topic = 'gateway/' + os.getenv('PPM_ORG') + '/' + os.getenv('PPM_PCODE')
        LOGGER.info('topic :%s', topic)
        
        pcStream = Stream(0, '')
        phoneStream = Stream(0, '')

        while True:
            try:
                async with client:
                    await client.subscribe(topic)
                    async for message in client.messages:
                        msg = json.loads(message.payload)
                        match msg['cmd']:
                            case 'open':
                                pullURL, pushURL = await buildCommand(str(msg['type']), msg['name'])
                                if msg['type'] == '0':    # Desktop
                                    if pcStream.pid != 0:
                                        await killProcess(pcStream.pid)
                                    pid = await pushStream(pullURL, pushURL)
                                    if pid != 0:
                                        pcStream.pid = pid
                                        pcStream.name = msg['name']
                                else:
                                    if phoneStream.pid != 0:
                                        await killProcess(phoneStream.pid)
                                    pid = await pushStream(pullURL, pushURL)
                                    if pid != 0:
                                        phoneStream.pid = pid
                                        phoneStream.name = msg['name']
                            
                            case 'stop':
                                if msg['type'] == '0':  # desktop
                                    LOGGER.info('close process id:%d', pcStream.pid )
                                    if pcStream.pid != 0:
                                        await killProcess(pcStream.pid)
                                        pcStream.pid = 0
                                        pcStream.name = ''
                                else:
                                    if phoneStream.pid != 0:
                                        await killProcess(phoneStream.pid)
                                        phoneStream.pid = 0
                                        phoneStream.name = ''
                            case 'capture':
                                pullURL, pushURL = await buildCommand(str(msg['type']), msg['name'])
                                await captureFrame(pullURL, msg['file'])
                            
                            case 'snapshot':
                                #download 30 sec video
                                
                                LOGGER.info('snapshot event time:%d', msg['eventTime'] )
                            case 'setup':
                                await configTables()
            except aiomqtt.MqttError:
                LOGGER.info('MQTT connection lost; Reconnecting ...')
                await asyncio.sleep(interval)
        

if __name__ == '__main__':
    load_dotenv()
    asyncio.run(main())