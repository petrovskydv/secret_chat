import json
import logging

from messenger.connection import get_connection
from messenger.messages import send_message, read_message, LINE_FEED
from messenger.storage import save_token_to_file

AUTH_PATH = 'settings/auth.ini'
logger = logging.getLogger('sender')


class UnknownToken(Exception):
    def __str__(self):
        return 'Unknown token. Check it out or register it again.'


async def authorise(reader, writer, token):
    text = f'{token}{LINE_FEED}'
    await send_message(writer, text)

    message = await read_message(reader)
    if message == f'null{LINE_FEED}':
        logger.error('Неизвестный токен. Проверьте его или зарегистрируйте заново.')
        raise UnknownToken()

    user = json.loads(message)
    nickname = user['nickname']
    logger.debug(f'Выполнена авторизация. Пользователь {nickname}')

    await read_message(reader)

    return nickname


async def register(host, port, username):
    async with get_connection(host, port) as (reader, writer):
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
