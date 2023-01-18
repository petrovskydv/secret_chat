import asyncio
from datetime import datetime

import aiofiles as aiofiles
import configargparse


async def listen_chat(host, port, log_path):
    token = '221522e6-9716-11ed-8c47-0242ac110002'
    reader, writer = await asyncio.open_connection(host, port)

    received_data = await reader.readline()
    text = f'[{datetime.now().strftime("%d.%m.%y %H:%M")}]: {received_data.decode()}'
    print(text)

    writer.write(f'{token}\n'.encode())
    await writer.drain()

    received_data = await reader.readline()
    text = f'[{datetime.now().strftime("%d.%m.%y %H:%M")}]: {received_data.decode()}'
    print(text)
    received_data = await reader.readline()
    text = f'[{datetime.now().strftime("%d.%m.%y %H:%M")}]: {received_data.decode()}'
    print(text)

    message = 'test message\n\n'
    print(f'Send: {message!r}')
    writer.write(message.encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()


if __name__ == '__main__':
    parser = configargparse.ArgParser(default_config_files=['settings.ini'], ignore_unknown_config_file_keys=True)
    parser.add_argument('-c', '--my-config', is_config_file=True, help='config file path')
    parser.add_argument('--host', required=True, help='chat server url')
    parser.add_argument('--sender_port', required=True, help='chat server port')
    parser.add_argument('--log_path', required=True, help='path to chat logs')
    args = parser.parse_args()

    asyncio.run(listen_chat(args.host, args.sender_port, args.log_path))
