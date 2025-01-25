import asyncio
from asyncio.subprocess import PIPE
from asyncio.streams import StreamReader
import shlex
import logging


LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


async def asyncRunShell(command):
    process = await asyncio.create_subprocess_shell(
        *shlex.split(command),
        stdout=PIPE, stderr=PIPE)

    stdout, stderr = await process.communicate()
    if stdout:
        LOGGER.info('stdout::%s', stdout.decode())
    if stderr:
        LOGGER.info('stderr::%s', stderr.decode())
    LOGGER.info('rtnCode::%s', process.returncode)
    return process.returncode, stdout.decode()


async def asyncRunExec(command):
    process = await asyncio.create_subprocess_exec(
        *shlex.split(command), stdout=PIPE, stderr=PIPE)
    stdout: StreamReader = process.stdout
    # 读取输出内容，如果子进程没有执行完毕，那么 await stdout.read() 会阻塞
    content = (await stdout.read()).decode('utf-8')
    await process.wait() # wait for the child process to exit
    #process.kill()
    return process.returncode, content


async def asyncRunNoWait(command):
    process = await asyncio.create_subprocess_exec(
        *shlex.split(command), stdout=PIPE, stderr=PIPE)
    # 會卡住
    #stdout, stderr = await process.communicate()
    if process.returncode is not None:
        await process.terminate()
        await process.kill()
    
    return process.pid, process.returncode

