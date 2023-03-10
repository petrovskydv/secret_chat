import asyncio
import logging
from datetime import datetime

import aiofiles as aiofiles
import configargparse

from messenger.connection import get_connection


async def listen_chat(host, port, log_path):
    async with get_connection(host, port) as (reader, writer):
        async with aiofiles.open(log_path, mode='a') as f:
            while message := await reader.readline():
                text = f'[{datetime.now().strftime("%d.%m.%y %H:%M")}]: {message.decode()}'
                logging.info(text)
                await f.write(text)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')

    parser = configargparse.ArgParser(
        default_config_files=['settings/settings.ini'],
        ignore_unknown_config_file_keys=True,
        description='Listener for dvmn chat',
    )
    parser.add_argument('-c', '--config', is_config_file=True, help='config file path')
    parser.add_argument('--host', required=True, help='chat server url')
    parser.add_argument('--port', required=True, help='chat server port')
    parser.add_argument('--log_path', required=True, help='path to chat logs')
    args = parser.parse_args()

    asyncio.run(listen_chat(args.host, args.port, args.log_path))
