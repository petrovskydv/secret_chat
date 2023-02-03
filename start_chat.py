import asyncio
import contextlib
import logging
import tkinter as tk
from tkinter import messagebox

import configargparse
from anyio import create_task_group

from messenger import gui, chat_client

from messenger.msg_history import read_history, save_messages
from messenger.storage import read_token_from_file

AUTH_PATH = 'settings/auth.ini'


async def main():
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

    parser = configargparse.ArgParser(
        default_config_files=['settings/settings.ini'],
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
        messagebox.showinfo('Пользователь не зарегистрирован.', 'Нужно пройти регистрацию в чате.')
        return

    token_error_event = asyncio.Event()

    async with create_task_group() as tg:
        await tg.start(read_history, args.log_path, messages_queue)
        await tg.start(gui.draw, messages_queue, sending_queue, status_updates_queue, token_error_event)
        await tg.start(save_messages, args.log_path, saving_queue)
        await tg.start(chat_client.handle_connection, args.host, args.port, args.sender_port, token, messages_queue,
                       sending_queue, saving_queue, status_updates_queue, token_error_event)


if __name__ == '__main__':
    with contextlib.suppress(tk.TclError, KeyboardInterrupt, gui.TkAppClosed):
        asyncio.run(main())
