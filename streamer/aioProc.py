import asyncio
from asyncio.subprocess import Process, PIPE
from asyncio.streams import StreamReader
import shlex
import logging
import psutil


LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

async def killSubProcess(pid):
    process = psutil.Process(pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()


async def asyncRunWait(command):
    process = await asyncio.create_subprocess_exec(
        *shlex.split(command), 
        stdout=asyncio.subprocess.DEVNULL,
        stderr=PIPE)
    
    # 會卡住
    stdout, stderr = await process.communicate()
    #await process.wait()
    if stderr is not None:
        await process.terminate()
        await process.kill()
    
    return process.returncode

async def asyncOutput(command):
    process = await asyncio.create_subprocess_exec(
        *shlex.split(command), 
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    stdout: StreamReader = process.stdout
    # 读取输出内容，如果子进程没有执行完毕，那么 await stdout.read() 会阻塞
    content = (await stdout.read()).decode('utf-8')
    await process.wait() # wait for the child process to exit
    #process.kill()
    return process.returncode, content

    
async def asyncRunNoWait(command):
    process = await asyncio.create_subprocess_exec(
        *shlex.split(command), 
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    # 會卡住
    #stdout, stderr = await process.communicate()
    if process.returncode is not None:
        await process.terminate()
        await process.kill()
    
    return process.pid, process.returncode

