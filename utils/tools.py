import asyncio
import json
import logging

logger = logging.getLogger('sender')


class UnknownToken(Exception):
    def __str__(self):
        return 'Unknown token. Check it out or register it again.'


async def send_message(writer, text):
    writer.write(text.encode())
    logger.debug(f'send: {text}')
    await writer.drain()


async def read_message(reader):
    received_data = await reader.readline()
    message = received_data.decode()
    logger.debug(f'receive: {message}')
    return message


async def get_connection(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    # при подключении всегда проспускаем первое сообщение
    await read_message(reader)
    return reader, writer


async def raise_for_invalid_token(message):
    user = json.loads(message)
    if not user:
        logger.error('Неизвестный токен. Проверьте его или зарегистрируйте заново.')
        raise UnknownToken()
