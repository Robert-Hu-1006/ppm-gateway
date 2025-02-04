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
    try:
        process = psutil.Process(pid)
        name = process.name()
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()
    except psutil.NoSuchProcess:
        pass
    else:
        LOGGER.info('process: %s running with pid: %d', name, pid)


async def asyncRunWait(command):
    process = await asyncio.create_subprocess_exec(
        *shlex.split(command), 
        stdout=PIPE,
        stderr=PIPE)
    # asyncio.subprocess.DEVNULL    才不會卡住
    #stdout: StreamReader = process.stdout
    
    while process.returncode is None:
        await asyncio.sleep(0.5)
    
    stdout, stderr = await process.communicate()
    LOGGER.info('async wait return err:%s', stderr.decode())
    #if len(stderr) > 0:
    #    await process.terminate()
    #    await process.kill()
    
    return stderr.decode()

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
        LOGGER.info('async no wait rtn:%s', process.returncode)
        await process.terminate()
        await process.kill()
    
    return process.pid, process.returncode

