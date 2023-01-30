import logging

import aiofiles
from anyio import TASK_STATUS_IGNORED


async def save_messages(filepath, queue, task_status=TASK_STATUS_IGNORED):
    task_status.started()
    async with aiofiles.open(filepath, mode='a') as f:
        while True:
            message = await queue.get()
            await f.write(f'{message}\n')


async def read_history(filepath, queue):
    logging.debug('read msgs from history')
    async with aiofiles.open(filepath, mode='r') as f:
        while msg := await f.readline():
            queue.put_nowait(msg.strip())
    logging.debug('read msgs from history finish')
