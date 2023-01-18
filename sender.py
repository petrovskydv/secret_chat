import asyncio
import json
import logging
from datetime import datetime

import configargparse

logger = logging.getLogger('sender')


async def send_message(host, port, log_path):
    token = '221522e6-9716-11ed-8c47-0242ac110002'
    reader, writer = await asyncio.open_connection(host, port)

    received_data = await reader.readline()
    text = f'{received_data.decode()!r}'
    logger.debug(text)

    writer.write(f'{token}\n'.encode())
    logger.debug(token)
    await writer.drain()

    received_data = await reader.readline()
    text = f'{received_data.decode()!r}'
    logger.debug(text)
    user = json.loads(received_data.decode().strip())
    if not user:
        logger.error('Неизвестный токен. Проверьте его или зарегистрируйте заново.')
        return

    received_data = await reader.readline()
    text = f'{received_data.decode()!r}'
    logger.debug(text)

    message = 'test message\n\n'
    logger.debug(f'Send: {message!r}')
    writer.write(message.encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

    parser = configargparse.ArgParser(default_config_files=['settings.ini'], ignore_unknown_config_file_keys=True)
    parser.add_argument('-c', '--my-config', is_config_file=True, help='config file path')
    parser.add_argument('--host', required=True, help='chat server url')
    parser.add_argument('--sender_port', required=True, help='chat server port')
    parser.add_argument('--log_path', required=True, help='path to chat logs')
    args = parser.parse_args()

    asyncio.run(send_message(args.host, args.sender_port, args.log_path))
