import asyncio
import contextlib
import json
import logging
import time
import tkinter as tk
from datetime import datetime
from enum import Enum
from tkinter.scrolledtext import ScrolledText

import aiofiles
import configargparse

from sender import AUTH_PATH, LINE_FEED, authorise, submit_message
from utils.storage import read_token_from_file
from utils.tools import get_connection, UnknownToken, read_message, send_message


class TkAppClosed(Exception):
    pass


class ReadConnectionStateChanged(Enum):
    INITIATED = 'устанавливаем соединение'
    ESTABLISHED = 'соединение установлено'
    CLOSED = 'соединение закрыто'

    def __str__(self):
        return str(self.value)


class SendingConnectionStateChanged(Enum):
    INITIATED = 'устанавливаем соединение'
    ESTABLISHED = 'соединение установлено'
    CLOSED = 'соединение закрыто'

    def __str__(self):
        return str(self.value)


class NicknameReceived:
    def __init__(self, nickname):
        self.nickname = nickname


def process_new_message(input_field, sending_queue):
    text = input_field.get()
    sending_queue.put_nowait(text)
    input_field.delete(0, tk.END)


async def update_tk(root_frame, interval=1 / 120):
    while True:
        try:
            root_frame.update()
        except tk.TclError:
            # if application has been destroyed/closed
            raise TkAppClosed()
        await asyncio.sleep(interval)


async def update_conversation_history(panel, messages_queue):
    while True:
        msg = await messages_queue.get()

        panel['state'] = 'normal'
        if panel.index('end-1c') != '1.0':
            panel.insert('end', '\n')
        panel.insert('end', msg)
        # TODO сделать промотку умной, чтобы не мешала просматривать историю сообщений
        # ScrolledText.frame
        # ScrolledText.vbar
        panel.yview(tk.END)
        panel['state'] = 'disabled'


async def update_status_panel(status_labels, status_updates_queue):
    nickname_label, read_label, write_label = status_labels

    read_label['text'] = f'Чтение: нет соединения'
    write_label['text'] = f'Отправка: нет соединения'
    nickname_label['text'] = f'Имя пользователя: неизвестно'

    while True:
        msg = await status_updates_queue.get()
        if isinstance(msg, ReadConnectionStateChanged):
            read_label['text'] = f'Чтение: {msg}'

        if isinstance(msg, SendingConnectionStateChanged):
            write_label['text'] = f'Отправка: {msg}'

        if isinstance(msg, NicknameReceived):
            nickname_label['text'] = f'Имя пользователя: {msg.nickname}'


def create_status_panel(root_frame):
    status_frame = tk.Frame(root_frame)
    status_frame.pack(side="bottom", fill=tk.X)

    connections_frame = tk.Frame(status_frame)
    connections_frame.pack(side="left")

    nickname_label = tk.Label(connections_frame, height=1, fg='grey', font='arial 10', anchor='w')
    nickname_label.pack(side="top", fill=tk.X)

    status_read_label = tk.Label(connections_frame, height=1, fg='grey', font='arial 10', anchor='w')
    status_read_label.pack(side="top", fill=tk.X)

    status_write_label = tk.Label(connections_frame, height=1, fg='grey', font='arial 10', anchor='w')
    status_write_label.pack(side="top", fill=tk.X)

    return nickname_label, status_read_label, status_write_label


async def draw(messages_queue, sending_queue, status_updates_queue):
    root = tk.Tk()

    root.title('Чат Майнкрафтера')

    root_frame = tk.Frame()
    root_frame.pack(fill="both", expand=True)

    status_labels = create_status_panel(root_frame)

    input_frame = tk.Frame(root_frame)
    input_frame.pack(side="bottom", fill=tk.X)

    input_field = tk.Entry(input_frame)
    input_field.pack(side="left", fill=tk.X, expand=True)

    input_field.bind("<Return>", lambda event: process_new_message(input_field, sending_queue))

    send_button = tk.Button(input_frame)
    send_button["text"] = "Отправить"
    send_button["command"] = lambda: process_new_message(input_field, sending_queue)
    send_button.pack(side="left")

    conversation_panel = ScrolledText(root_frame, wrap='none')
    conversation_panel.pack(side="top", fill="both", expand=True)

    await asyncio.gather(
        update_tk(root_frame),
        update_conversation_history(conversation_panel, messages_queue),
        update_status_panel(status_labels, status_updates_queue)
    )


async def read_msgs(host, port, messages_queue, saving_queue):
    async with get_connection(host, port) as connection:
        reader, writer = connection
        while message := await reader.readline():
            logging.debug(f'receive new message: {message.strip().decode()}')
            text = f'[{datetime.now().strftime("%d.%m.%y %H:%M")}]: {message.strip().decode()}'
            messages_queue.put_nowait(text)
            saving_queue.put_nowait(text)


async def save_messages(filepath, queue):
    async with aiofiles.open(filepath, mode='a') as f:
        while True:
            message = await queue.get()
            await f.write(f'{message}\n')


async def read_history(filepath, queue):
    logging.debug('read msgs from history')
    async with aiofiles.open(filepath, mode='r') as f:
        while msg := await f.readline():
            queue.put_nowait(msg.strip())
    logging.debug('read msgs from history finish')


async def send_msgs(host, port, token, queue):
    async with get_connection(host, port) as connection:
        reader, writer = connection
        await read_message(reader)

        await authorise(reader, writer, token)

        while True:
            message = await queue.get()
            await submit_message(writer, message)


async def main():
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')

    parser = configargparse.ArgParser(
        default_config_files=['settings.ini'],
        ignore_unknown_config_file_keys=True,
        description='Listener for dvmn chat',
    )
    parser.add_argument('-c', '--config', is_config_file=True, help='config file path')
    parser.add_argument('--host', required=True, help='chat server url')
    parser.add_argument('--port', required=True, help='chat server port')
    parser.add_argument('--sender_port', required=True, help='chat server port')
    parser.add_argument('--log_path', required=True, help='path to chat logs')
    args = parser.parse_args()

    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    saving_queue = asyncio.Queue()

    try:
        token = await read_token_from_file(AUTH_PATH)
    except FileNotFoundError:
        raise UnknownToken()

    await asyncio.gather(
        draw(messages_queue, sending_queue, status_updates_queue),
        read_history(args.log_path, messages_queue),
        read_msgs(args.host, args.port, messages_queue, saving_queue),
        save_messages(args.log_path, saving_queue),
        send_msgs(args.host, args.sender_port, token, sending_queue),

    )


if __name__ == '__main__':
    # with contextlib.suppress(tk.TclError):
    #     asyncio.run(main(args.host, args.port))
    asyncio.run(main())
