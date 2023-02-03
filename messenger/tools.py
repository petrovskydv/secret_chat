import asyncio
import functools
import json
import logging
import textwrap
from contextlib import asynccontextmanager, suppress

from messenger.storage import save_token_to_file

LINE_FEED = '\n'
AUTH_PATH = 'settings/auth.ini'
logger = logging.getLogger('sender')


class UnknownToken(Exception):
    def __str__(self):
        return 'Unknown token. Check it out or register it again.'


async def send_message(writer, text):
    writer.write(text.encode())
    logger.debug(f'send: {text.rstrip(LINE_FEED)}')
    await writer.drain()


async def read_message(reader):
    received_data = await reader.readline()
    message = received_data.decode()
    logger.debug(f'receive: {message.rstrip(LINE_FEED)}')
    return message


@asynccontextmanager
async def get_connection(host, port):
    try:
        logger.debug(f'open connection to {host}:{port}')
        reader, writer = await asyncio.open_connection(host, port)
        yield reader, writer
    finally:
        with suppress(UnboundLocalError):
            logger.debug(f'close connection {host}:{port}')
            writer.close()
            await writer.wait_closed()


def reconnect(
        start_sleep_time: float = 0.1,
        factor: int = 2,
        border_sleep_time: float = 10,
        exceptions: tuple = Exception,
        logger: logging.Logger = None
):
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            _tries = 1
            _delay = start_sleep_time
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    _tries += 1
                    _delay = min(start_sleep_time * (factor ** _tries), border_sleep_time)
                    msg = f"""\
                    Function: {func.__name__}
                    Exception: {e}
                    Retrying in {_delay} seconds!"""
                    if logger:
                        logger.debug(textwrap.dedent(msg))
                    await asyncio.sleep(_delay)

        return wrapped

    return wrapper


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