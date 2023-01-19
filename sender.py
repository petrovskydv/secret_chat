import asyncio
import json
import logging

import configargparse

from utils.storage import save_token_to_file, read_token_from_file
from utils.tools import send_message, read_message, get_connection, UnknownToken, raise_for_invalid_token

logger = logging.getLogger('sender')
AUTH_PATH = 'auth.ini'
LINE_FEED = '\n'


async def send_message_from_cli(host, port, message, username=None):
    if username:
        token = await register(host, port, username)
    else:
        try:
            token = await read_token_from_file(AUTH_PATH)
        except FileNotFoundError:
            raise UnknownToken()

    async with get_connection(host, port) as connection:
        reader, writer = connection

        await read_message(reader)

        await authorise(reader, writer, token)
        await submit_message(writer, message)


async def submit_message(writer, message):
    text = f'{message}{LINE_FEED}{LINE_FEED}'
    await send_message(writer, text)


async def authorise(reader, writer, token):
    text = f'{token}{LINE_FEED}'
    await send_message(writer, text)

    message = await read_message(reader)
    if message == f'null{LINE_FEED}':
        logger.error('Неизвестный токен. Проверьте его или зарегистрируйте заново.')
        raise UnknownToken()

    await read_message(reader)


async def register(host, port, username):
    async with get_connection(host, port) as connection:
        reader, writer = connection

        await read_message(reader)

        text = f'{LINE_FEED}'
        await send_message(writer, text)

        await read_message(reader)

        text = f'{username}{LINE_FEED}'
        await send_message(writer, text)

        message = await read_message(reader)

    user = json.loads(message)
    token = user['account_hash']
    await save_token_to_file(AUTH_PATH, token)

    return token


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

    parser = configargparse.ArgParser(default_config_files=['settings.ini'], ignore_unknown_config_file_keys=True)
    parser.add_argument('-c', '--config', is_config_file=True, help='config file path')
    parser.add_argument('--host', required=True, help='chat server url')
    parser.add_argument('--sender_port', required=True, help='chat server port')
    parser.add_argument('-username', help='username for register in chat')
    parser.add_argument('message', help='message to chat')
    args = parser.parse_args()

    asyncio.run(send_message_from_cli(args.host, args.sender_port, args.message, args.username))
