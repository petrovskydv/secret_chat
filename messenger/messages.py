import logging

logger = logging.getLogger(__name__)


async def send_message(writer, text):
    writer.write(text.encode())
    logger.debug(f'send: {text.rstrip(LINE_FEED)}')
    await writer.drain()


async def read_message(reader):
    received_data = await reader.readline()
    message = received_data.decode()
    logger.debug(f'receive: {message.rstrip(LINE_FEED)}')
    return message


async def submit_message(writer, message):
    text = f'{message}{LINE_FEED}{LINE_FEED}'
    await send_message(writer, text)


LINE_FEED = '\n'
