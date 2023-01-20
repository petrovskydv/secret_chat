import logging

import aiofiles


async def save_messages(filepath, queue):
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
