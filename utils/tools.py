import asyncio
import logging
from contextlib import asynccontextmanager, suppress

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
        reader, writer = await asyncio.open_connection(host, port)
        yield reader, writer
    finally:
        with suppress(UnboundLocalError):
            logger.debug(f'close connection {host}:{port}')
            writer.close()
            await writer.wait_closed()
