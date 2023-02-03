import asyncio
import logging

import configargparse

from messenger.storage import read_token_from_file
from messenger.tools import UnknownToken, authorise, register, AUTH_PATH
from messenger.connection import get_connection
from messenger.messages import read_message, submit_message

logger = logging.getLogger('sender')


async def send_message_from_cli(host, port, message, username=None):
    if username:
        token = await register(host, port, username)
    else:
        try:
            token = await read_token_from_file(AUTH_PATH)
        except FileNotFoundError:
            raise UnknownToken()

    async with get_connection(host, port) as (reader, writer):

        await read_message(reader)

        await authorise(reader, writer, token)
        await submit_message(writer, message)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

    parser = configargparse.ArgParser(
        default_config_files=['settings/settings.ini'],
        ignore_unknown_config_file_keys=True
    )
    parser.add_argument('-c', '--config', is_config_file=True, help='config file path')
    parser.add_argument('--host', required=True, help='chat server url')
    parser.add_argument('--sender_port', required=True, help='chat server port')
    parser.add_argument('-username', help='username for register in chat')
    parser.add_argument('message', help='message to chat')
    args = parser.parse_args()

    asyncio.run(send_message_from_cli(args.host, args.sender_port, args.message, args.username))
