import asyncio
import json
import logging

import configargparse

from storage import save_token, read_token

logger = logging.getLogger('sender')
auth_path = 'auth.ini'


class UnknownToken(Exception):
    def __str__(self):
        return 'Unknown token. Check it out or register it again.'


async def send_message(host, port, message, username=None):
    if username:
        token = await register(host, port, username)
    else:
        try:
            token = await read_token(auth_path)
        except FileNotFoundError:
            raise UnknownToken()

    writer = await authorise(host, port, token)

    await submit_message(f'{message}\n\n', writer)


async def submit_message(message, writer):
    logger.debug(f'Send: {message!r}')
    writer.write(message.encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def authorise(host, port, token):
    reader, writer = await get_reader_writer(host, port)

    writer.write(f'{token}\n'.encode())
    logger.debug(token)
    await writer.drain()

    received_data = await reader.readline()
    text = f'{received_data.decode()!r}'
    logger.debug(text)
    user = json.loads(received_data.decode().strip())
    if not user:
        logger.error('Неизвестный токен. Проверьте его или зарегистрируйте заново.')
        raise UnknownToken()

    received_data = await reader.readline()
    text = f'{received_data.decode()!r}'
    logger.debug(text)
    return writer


async def register(host, port, username):
    reader, writer = await get_reader_writer(host, port)

    writer.write('\n'.encode())
    logger.debug('send empty token')
    await writer.drain()

    received_data = await reader.readline()
    text = f'{received_data.decode()!r}'
    logger.debug(text)

    writer.write(f'{username}\n'.encode())
    logger.debug(username)
    await writer.drain()

    received_data = await reader.readline()
    text = f'{received_data.decode()!r}'
    logger.debug(text)

    user = json.loads(received_data.decode().strip())
    token = user['account_hash']
    await save_token(auth_path, token)

    writer.close()
    await writer.wait_closed()

    return token


async def get_reader_writer(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    received_data = await reader.readline()
    text = f'{received_data.decode()!r}'
    logger.debug(text)
    return reader, writer


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

    parser = configargparse.ArgParser(default_config_files=['settings.ini'], ignore_unknown_config_file_keys=True)
    parser.add_argument('-c', '--my-config', is_config_file=True, help='config file path')
    parser.add_argument('--host', required=True, help='chat server url')
    parser.add_argument('--sender_port', required=True, help='chat server port')
    parser.add_argument('--log_path', required=True, help='path to chat logs')
    parser.add_argument('-username', help='username for register in chat')
    parser.add_argument('message', help='message to chat')
    args = parser.parse_args()

    asyncio.run(send_message(args.host, args.sender_port, args.message, args.username))
