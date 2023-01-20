import asyncio
import logging
import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText

import configargparse

import chat_client
from msg_history import save_messages, read_history
from utils.storage import read_token_from_file

AUTH_PATH = 'auth.ini'


class TkAppClosed(Exception):
    pass


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
        if isinstance(msg, chat_client.ReadConnectionStateChanged):
            read_label['text'] = f'Чтение: {msg}'

        if isinstance(msg, chat_client.SendingConnectionStateChanged):
            write_label['text'] = f'Отправка: {msg}'

        if isinstance(msg, chat_client.NicknameReceived):
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


async def main():
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

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
        messagebox.showinfo('Пользователь не зарегистрирован.', 'Нужно пройти регистрацию в чате.')
        return

    await read_history(args.log_path, messages_queue)

    await asyncio.gather(
        draw(messages_queue, sending_queue, status_updates_queue),
        save_messages(args.log_path, saving_queue),
        chat_client.handle_connection(args.host, args.port, args.sender_port, token, messages_queue, sending_queue,
                                      saving_queue, status_updates_queue)
    )


if __name__ == '__main__':
    # with contextlib.suppress(tk.TclError):
    #     asyncio.run(main(args.host, args.port))
    asyncio.run(main())
