import logging

import aiofiles

logger = logging.getLogger(__name__)


async def save_token_to_file(auth_path, token):
    logger.debug(f'save token to {auth_path}')
    async with aiofiles.open(auth_path, mode='w') as f:
        await f.write(token)


async def read_token_from_file(auth_path):
    logger.debug(f'read token from {auth_path}')
    async with aiofiles.open(auth_path, mode='r') as f:
        token = await f.readline()
    return token
