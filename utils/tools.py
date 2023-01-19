import asyncio
import json
import logging
from contextlib import asynccontextmanager

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


@asynccontextmanager
async def get_connection(host, port):
    try:
        logger.debug(f'open connection to {host}:{port}')
        connection = await asyncio.open_connection(host, port)
        reader, writer = connection
        yield connection
    finally:
        logger.debug('close connection')
        writer.close()
        await writer.wait_closed()
