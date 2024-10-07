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


async def genTelegrafTag(sheet):
    ppm_tag = '/etc/telegraf/tag/ppm_tag.json'
    sensorTable = {}

    if os.path.isfile(ppm_tag):
        os.remove(ppm_tag)
    wrkSheet = sheet.worksheet_by_title('Sensor')
    gTable = wrkSheet.get_values('A2', 'N')
    for i in range(len(gTable) - 1):
        deviceID = gTable[i + 1][2].lower()
        dataChannel = gTable[i + 1][6].lower()
        key = deviceID + '_' + dataChannel
        sensorTable[key] = {}
        sensorTable[key]['org'] =  gTable[i + 1][0]
        sensorTable[key]['code'] =  gTable[i + 1][1]
        sensorTable[key]['device'] =  gTable[i + 1][3]
        sensorTable[key]['sensor'] =  gTable[i + 1][5]
        sensorTable[key]['alarm'] =  gTable[i + 1][7]
        sensorTable[key]['floor'] =  gTable[i + 1][8]
        sensorTable[key]['area'] =  gTable[i + 1][9]
        sensorTable[key]['priority'] =  gTable[i + 1][10]
        sensorTable[key]['sop'] =  gTable[i + 1][11]
        sensorTable[key]['source'] =  gTable[i + 1][12]
        sensorTable[key]['cam_link'] =  gTable[i + 1][13]

    with open(ppm_tag, 'w') as SensorFile:
        json.dump(sensorTable, SensorFile, indent=2)
    SensorFile.close


async def killProcess(pid):
    process = psutil.Process(pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()
    #os.killpg(pid, signal.SIGUSR1)


async def pushStream(pull_url, push_url):
    LOGGER.info('pull url:%s', pull_url)
    LOGGER.info('push url:%s', push_url)
    #pull_url = 'rtsp://admin:Az123567@192.168.18.7:7001/bbf6e391-beb5-828a-64f7-86677fb65430'
    #push_url = 'rtsp://127.0.0.1:8554/live/h1'
    command = ['ffmpeg',
                '-rtsp_transport', 'tcp',
                '-i', pull_url,
                '-c', 'copy',
                '-f', 'rtsp',
                '-preset', 'ultrafast',
                push_url]

    #process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    process = subprocess.Popen(command, start_new_session=True)
    
    if process.returncode is None:
        rtnPID = process.pid
        rtnCode = 0
    else:
        rtnPID = 0
        rtnCode = process.returncode
        process.kill()
        LOGGER.info('error::%s', str(process.returncode))
    return rtnPID, rtnCode
   
    #ffmpeg -rtsp_transport tcp -i rtsp://admin:Az123567@192.168.18.7:7001/bbf6e391-beb5-828a-64f7-86677fb65430 \
    #-preset ultrafast \
    #-c copy -f rtsp rtsp://127.0.0.1:8554/stream/h1 
async def loadPingTable(sheet):
    pingTable = {}
    wrkSheet = sheet.worksheet_by_title('Sensor')
    gSheet = wrkSheet.get_values('A2', 'K')
    config = configparser.ConfigParser(strict=False)
    pCode = os.getenv('PPM_PCODE')
    
    ipList = []
    if os.path.isfile('/etc/telegraf/conf/ping.conf'):
        os.remove('/etc/telegraf/conf/ping.conf')
    #if os.path.isfile('./streamer/ping.conf'):
    #    os.remove('./streamer/ping.conf')

    for i in range(len(gSheet)-1):
        if gSheet[i + 1][1] == pCode: 
            ip = gSheet[i + 1][4]
            if ip not in ipList:
                config['[inputs.ping]'] = {}
                ipList.append(ip)
                config['[inputs.ping]']['urls'] = '["' + gSheet[i + 1][4] + '"]'
                config['[inputs.ping]']['method'] = '"exec"'
                config['[inputs.ping]']['count'] = '3'
                config['[inputs.ping]']['interval'] = '"15s"'

                config['inputs.ping.tags'] = {}
                config['inputs.ping.tags']['ID'] = '"' + gSheet[i + 1][2].lower() + '"'
                if len(gSheet[i + 1][2]) == 36:
                    config['inputs.ping.tags']['type'] = '"' + 'cam' + '"'
                else:
                    config['inputs.ping.tags']['type'] = '"' + 'iot' + '"'

                config['inputs.ping.tags']['name'] = '"' + gSheet[i + 1][3] + '"'
                config['inputs.ping.tags']['floor'] = '"' + gSheet[i + 1][9] + '"'
                config['inputs.ping.tags']['area'] = '"' + gSheet[i + 1][10] + '"'
    
            with open('/etc/telegraf/conf/ping.conf', 'a') as configfile:
            #with open('./streamer/ping.conf', 'a') as configfile:
                config.write(configfile)
                config = configparser.ConfigParser(strict=False)
            configfile.close

    wrkSheet = sheet.worksheet_by_title('LiveCam')
    gSheet = wrkSheet.get_values('A2', 'K')
    for j in range(len(gSheet)-1):
        if gSheet[j + 1][1] == pCode: 
            ip = gSheet[i + 1][7]
            if ip not in ipList:
                config['[inputs.ping]'] = {}
                ipList.append(ip)
                config['[inputs.ping]']['urls'] = '["' + gSheet[i + 1][7] + '"]'
                config['[inputs.ping]']['method'] = '"exec"'
                config['[inputs.ping]']['count'] = '3'
                config['[inputs.ping]']['interval'] = '"15s"'

                config['inputs.ping.tags'] = {}
                config['inputs.ping.tags']['ID'] = '"' + gSheet[i + 1][2].lower() + '"'
                config['inputs.ping.tags']['type'] = '"' + 'cam' + '"'
                config['inputs.ping.tags']['name'] = '"' + gSheet[i + 1][3] + '"'
                config['inputs.ping.tags']['floor'] = '"' + gSheet[i + 1][5] + '"'
                config['inputs.ping.tags']['area'] = '"' + gSheet[i + 1][6] + '"'
    
            with open('/etc/telegraf/conf/ping.conf', 'a') as configfile:
            # with open('./streamer/ping.conf', 'a') as configfile:
                config.write(configfile)
                config = configparser.ConfigParser(strict=False)
            configfile.close    
    
async def loadCamTable(wrkSheet):
    camTable = {}
    pCode = os.getenv('PPM_PCODE')
    gSheet = wrkSheet.get_values('A2', 'L')
    for i in range(len(gSheet) - 1):
        if gSheet[i + 1][1] == pCode:
            name = gSheet[i + 1][3]
            camTable[name] = {}
            camTable[name]['code'] =  gSheet[i + 1][1]
            camTable[name]['cam_id'] =  gSheet[i + 1][2]
            camTable[name]['path'] =  gSheet[i + 1][4]
            camTable[name]['floor'] =  gSheet[i + 1][5]
            camTable[name]['area'] =  gSheet[i + 1][6]
            camTable[name]['ip'] =  gSheet[i + 1][7]
            camTable[name]['port'] =  gSheet[i + 1][8]
            camTable[name]['account'] =  gSheet[i + 1][9]
            camTable[name]['passwd'] =  gSheet[i + 1][10]
            camTable[name]['token'] =  gSheet[i + 1][11]

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
            async with session.get(downloadURL, headers=headers) as response:
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
    
async def main():
    global LICENSE
    LICENSE = await getLicenseInfo()
    if 'expire' in LICENSE.keys():
        LOGGER.info('license expire date:%s', LICENSE['expire'])

    await downloadGoogleKey()
    await configTables()
    await genTelegrafTag()
    
    client = aiomqtt.Client(
                    hostname=os.getenv('PPM_CLOUD'),
                    port=int(os.getenv('MQTT_PORT')),
                    username=os.getenv('MQTT_USR'),
                    password=os.getenv('MQTT_PWD')
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
                            pullURL = 'rtsp://' + CAM_TABLE[msg['name']]['account'] + ':' + \
                                CAM_TABLE[msg['name']]['passwd'] + '@' + \
                                CAM_TABLE[msg['name']]['ip'] + ':' + \
                                CAM_TABLE[msg['name']]['port'] + '/' + \
                                CAM_TABLE[msg['name']]['path'] + \
                                CAM_TABLE[msg['name']]['cam_id']

                            pushURL = 'rtsp://' + os.getenv('PPM_CLOUD') + ':8554/live/' + \
                                    str(msg['type']) + '/' + \
                                    os.getenv('PPM_ORG') + '/' + \
                                    msg['name']

                            if msg['type'] == 0:
                                if pcStream.pid != 0:
                                    await killProcess(pcStream.pid)
                            
                                pid, rtnCode = await pushStream(pullURL, pushURL)
                                if rtnCode == 0:
                                    pcStream.pid = pid
                                    pcStream.name = msg['name']
                            else:
                                if phoneStream.pid != 0:
                                    await killProcess(phoneStream.pid)
                            
                                pid, rtnCode = await pushStream(pullURL, pushURL)
                                if rtnCode == 0:
                                    phoneStream.pid = pid
                                    phoneStream.name = msg['name']
                        
                        case 'close':
                            if msg['type'] == 0:
                                if pcStream.pid != 0:
                                    await killProcess(pcStream.pid)
                                    pcStream.pid = 0
                                    pcStream.name = ''
                            else:
                                if phoneStream.pid != 0:
                                    await killProcess(phoneStream.pid)
                                    phoneStream.pid = 0
                                    phoneStream.name = ''
                        case 'setup':
                            await configTables()
        except aiomqtt.MqttError:
            LOGGER.info('MQTT connection lost; Reconnecting ...')
            await asyncio.sleep(interval)
    

if __name__ == '__main__':
    load_dotenv()
    asyncio.run(main())