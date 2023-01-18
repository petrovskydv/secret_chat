import logging

import aiofiles

logger = logging.getLogger(__name__)


async def save_token(auth_path, token):
    logger.debug('save token to {auth_path}')
    async with aiofiles.open(auth_path, mode='w') as f:
        await f.write(token)


async def read_token(auth_path):
    logger.debug('read token from {auth_path}')
    async with aiofiles.open(auth_path, mode='r') as f:
        token = await f.readline()
    return token
