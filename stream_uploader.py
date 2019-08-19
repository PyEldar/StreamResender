import socket
import threading
import logging
import time


class EndOfStreamException(Exception):
    pass


class StreamUploader:
    def __init__(self, url, trigger_port, imgs):
        self.url = url
        self.trigger_port = trigger_port
        self.should_upload = threading.Event()
        self.imgs = imgs

    def handle_trigger(self):
        threading.Thread(target=self._trigger_loop).start()

    def _trigger_loop(self):
        logging.debug('creating trigger socket')
        trigger_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        trigger_socket.connect((self.url, self.trigger_port))
        try:
            logging.info('Trigger socket connected')
            while True:
                logging.debug('waiting for remote trigger')
                self._wait_for_data(trigger_socket, b'send_data')
                self.should_upload.set()
                while True:
                    try:
                        data_start_port = int(trigger_socket.recv(9).decode().strip())
                        break
                    except ValueError:
                        logging.warning('Receive non numeric value as data_start_port from trigger_socket')
                self._start_upload(data_start_port)

                logging.debug('Waiting for remote close data trigger')
                self._wait_for_data(trigger_socket, b'close_data')
                self.should_upload.clear()
        except EndOfStreamException:
            logging.warning('End of stream detected on trigger socker')
        finally:
            trigger_socket.close()
            self.should_upload.clear()

    def _wait_for_data(self, socket, data):
        logging.debug('waiting for data {}'.format(data))
        recv_data = socket.recv(len(data))
        logging.debug('Received {}'.format(recv_data))
        while recv_data != data:
            recv_data = socket.recv(len(data))
            logging.debug('Received {}'.format(recv_data))
            if len(recv_data) == 0:
                raise EndOfStreamException()

    def _start_upload(self, start_port):
        logging.info('Starting senders')
        for i, key in enumerate(self.imgs.keys()):
            threading.Thread(target=self._send_stream, args=(start_port + i, key)).start()

    def _send_stream(self, port, image_key):
        logging.debug('Connecting sender to port {}'.format(port))
        data_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        data_socket.connect((self.url, port))
        try:
            logging.debug('Sender connected to port {} preparing to send image {}'.format(port, image_key))
            while self.imgs[image_key] is None:
                time.sleep(0.1)
            while self.should_upload.is_set():
                logging.debug('Sending image {} to port {}'.format(image_key, port))
                data_socket.sendall(str(len(self.imgs[image_key])).encode())
                data_socket.sendall(self.imgs[image_key])
        finally:
            data_socket.close()
