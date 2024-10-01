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
class Cprocess:
    pid = 0
    cam = ''

async def getMysqlPool():
    global MQTT_POOL

    if MQTT_POOL : return MQTT_POOL
    MQTT_POOL = aiomqtt.Client(
                            hostname=os.getenv('MQTT_HOST'),
                            port=int(os.getenv('MQTT_PORT')),
                            username=os.getenv('MQTT_USR'),
                            password=os.getenv('MQTT_PWD'),
                            client_id='apiserver')
                            #protocol=ProtocolVersion.V31
                #await conn.connect(timeout=60)
            
    print('Connect to MQTT Broker :: %s', str(MQTT_POOL))
    return MQTT_POOL

async def killProcess(pid):
    process = psutil.Process(pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()
    #os.killpg(pid, signal.SIGUSR1)
    Cprocess.pid = 0
    Cprocess.cam = ''


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

    #process = subprocess.run(command)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    try:
        output, error = process.communicate(timeout=2.5)
        LOGGER.info('output:%s error:%s', output.decode(), str(error.decode()))
        if process.returncode is None:
            rtnPID = process.pid
            rtnCode = 0
        #return rtnPID, rtnCode
    except subprocess.TimeoutExpired as e:
        rtnPID = 0
        rtnCode = 503
        process.kill()
    return rtnPID, rtnCode
   
    #ffmpeg -rtsp_transport tcp -i rtsp://admin:Az123567@192.168.18.7:7001/bbf6e391-beb5-828a-64f7-86677fb65430 \
    #-preset ultrafast \
    #-c copy -f rtsp rtsp://127.0.0.1:8554/stream/h1 
async def loadPingTable(wrkSheet):
    pingTable = {}
    gSheet = wrkSheet.get_values('A2', 'J')
    config = configparser.ConfigParser(strict=False)
    pCode = os.getenv('PPM_PCODE')

    idList = []
    for i in range(len(gSheet)-1):
        if gSheet[i + 1][1] == pCode: 
            print('config pCode ::', gSheet[i + 1][1])
            config['[inputs.ping]'] = {}
            deviceID = gSheet[i + 1][2].lower()
            if deviceID not in idList:
                idList.append(deviceID)
                config['[inputs.ping]']['urls'] = '["' + gSheet[i + 1][3] + '"]'
                config['[inputs.ping]']['method'] = '"exec"'
                config['[inputs.ping]']['count'] = '3'
                config['inputs.ping.tags'] = {}
                config['inputs.ping.tags']['ID'] = '"' + deviceID + '"'
                if len(deviceID) == 36:
                    config['inputs.ping.tags']['type'] = '"' + 'cam' + '"'
                else:
                    config['inputs.ping.tags']['type'] = '"' + 'iot' + '"'

                config['inputs.ping.tags']['name'] = '"' + gSheet[i + 1][4] + '"'
                config['inputs.ping.tags']['floor'] = '"' + gSheet[i + 1][8] + '"'
                config['inputs.ping.tags']['area'] = '"' + gSheet[i + 1][9] + '"'
        
        if os.path.isfile('ping.conf') :
            os.remove('ping.conf')
        with open('ping.conf', 'a') as configfile:
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

    with open('camTable.json', 'w', encoding='utf8') as camFile:
        json.dump(camTable, camFile, ensure_ascii=False, indent=2)
    camFile.close
    return i, camTable

async def configTables():
    try:
        client = pygsheets.authorize(service_account_file='./streamer/client_secret.json')
        sheet = client.open_by_key(LICENSE['sheet'])
        
        # reload camera table from google sheet
        wrkSheet = sheet.worksheet_by_title('LiveCam')
        count, CAM_TABLE = await loadCamTable(wrkSheet)
        if count == 0:
            CAM_TABLE = json.load(open('./streamer/camTable.json','r'))

        # reload ping table from google sheet for telegraf
        wrkSheet = sheet.worksheet_by_title('Sensor')
        await loadPingTable(wrkSheet)

    except Exception as e:
        LOGGER.info('Read Google Sheet Error :: %s', str(e))

async def getLicenseInfo():
    queryURL = 'http://' + os.getenv('PPM_CLOUD') + ':3010/api/ppm/license/query?org=' + os.getenv('PPM_ORG')
    headers = {
            "accept": "application/json",
            "Authorization": "Bearer " + os.getenv('API_TOKEN')
        }
    async with aiohttp.ClientSession() as session:
        async with session.get(queryURL, headers=headers) as response:
            if response.status == 200:
                licRtn = await response.json()
                return licRtn 
                #if searchRtn.get('message','') == 'user not found':
    
async def main():
    global LICENSE
    LICENSE = await getLicenseInfo()
    
    await configTables()
    
    client = aiomqtt.Client(
                    hostname=os.getenv('PPM_CLOUD'),
                    port=int(os.getenv('MQTT_PORT')),
                    username=os.getenv('MQTT_USR'),
                    password=os.getenv('MQTT_PWD')
                    )
    LOGGER.info('Connect MQTT Broker :%s', str(client))
    interval = 3  # Seconds
    topic = 'gateway/' + os.getenv('PPM_ORG') + '/' + os.getenv('P_CODE')
    LOGGER.info('topic :%s', topic)
    
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
                                CAM_TABLE[msg['name']]['host'] + ':' + \
                                CAM_TABLE[msg['name']]['port'] + '/' + \
                                CAM_TABLE[msg['name']]['path'] + \
                                CAM_TABLE[msg['name']]['cam_id']
                                
                            pushURL = 'rtsp://' + os.getenv('PPM_CLOUD') + ':8554/live/' + \
                                os.getenv('PPM_ORG') + '/' + \
                                msg['name']
                            
                            if Cprocess.pid != 0:
                                await killProcess(Cprocess.pid)
                            
                            pid, rtnCode = await pushStream(pullURL, pushURL)
                            
                            if rtnCode == 0:
                                Cprocess.pid = pid
                                Cprocess.cam = msg['name']
                                
                            print('err::', rtnCode)
                        case 'close':
                            print('clse::', Cprocess.pid)
                            if Cprocess.pid != 0:
                                await killProcess(Cprocess.pid)
                            
                    
        except aiomqtt.MqttError:
            print(f"Connection lost; Reconnecting in {interval} seconds ...")
            await asyncio.sleep(interval)
    

if __name__ == '__main__':
    load_dotenv()
    asyncio.run(main())