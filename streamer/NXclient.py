import asyncio
import aiohttp
import logging
import json
from datetime import datetime

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

async def extractFrame(camera, user, passwd, pullStart, snapID):
    LOGGER.info('')