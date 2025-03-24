import asyncio
from aiohttp import web
from multidict import CIMultiDict
import os, time, json
import netifaces
from os import system
from datetime import datetime, timedelta, timezone 
from dotenv import load_dotenv
import logging
import aiohttp_cors
from aiojobs.aiohttp import setup, spawn
#from aiohttp_tokenauth import token_auth_middleware

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

async def getIpAddress(request: web.Request):
    interface = os.getenv('INF')
    #eth0 = netifaces.ifaddresses('eth0')[2][0]['addr']
    eth0 = netifaces.ifaddresses(interface)[2][0]['addr']
    mask = netifaces.ifaddresses(interface)[2][0]['netmask']
    LOGGER.info('ethe0:%s', eth0)
    #wlan0 = netifaces.ifaddresses('wlan0')[2][0]['addr']
    inf ={
        "inf": interface,
        "ip": eth0,
        "mask": mask
    }
    return web.json_response(inf, status=200, content_type='application/json')

async def setIpAddress(request: web.Request):
    inf = await request.json()
    ipAddress = inf['ip']
    interface = inf['interface']
    LOGGER.info('ip:%s', ipAddress)
    os.system(f'sudo ifconfig {interface} down')
    os.system(f'sudo ifconfig {interface} {ipAddress}')
    os.system(f'sudo ifconfig {interface} up')
    return web.Response(status=200)

async def getHostEnv(request: web.Request):
    with open('/data/lic.json') as licFile:
        licData = json.load(licFile)
    LOGGER.info('expire : %s', licData['expire'])
    
    payload = {
        "domain": os.getenv('PPM_CLOUD'),
        "org": os.getenv('PPM_ORG'),
        "code": os.getenv('PPM_PCODE'),
        "expire": licData['expire']
    }
    return web.json_response(payload, status=200, content_type='application/json')

#async def startupTasks(app: web.Application) -> None:
#    app[SQL_CONN] = asyncio.create_task(initMySQL(app))
#    app[REDIS_CONN] = asyncio.create_task(initReids(app))
#    app[MQTT_CONN] = asyncio.create_task(initMQTT(app))

def initServer() -> web.Application:
    # Bearer Token
    #async def ValidateToken(token: str):
        # API 只給一個固定Token
    #    LOGGER.info('validate api token => %s', token)
    #    user = None
    #    if token == os.getenv('API_TOKEN'):
    #        user = {'uuid': 'ppm-api'}
    #    return user

    #app = web.Application(middlewares=[token_auth_middleware(ValidateToken)])
    app = web.Application()
    cors = aiohttp_cors.setup(app)

    app.add_routes([web.post('/api/gateway/ip', setIpAddress),
                    web.get('/api/gateway/ip', getIpAddress,),
                    web.get('/api/gateway/env', getHostEnv)
                    ])

    cors = aiohttp_cors.setup(app, defaults={
                                        "*": aiohttp_cors.ResourceOptions(
                                                allow_credentials=False,
                                                expose_headers="*",
                                                allow_headers="*"
                                            )
                                        })
    for route in list(app.router.routes()):
        cors.add(route)
    
    #app.on_startup.append(startupTasks)
    setup(app)
    return app


if __name__ == '__main__':
    #asyncio.run(getIpAddress())
    load_dotenv()
    API_PORT = int(os.getenv('API_PORT'))
    LOGGER.info('init api server port => %s', API_PORT)
    web.run_app(initServer(), port=API_PORT)