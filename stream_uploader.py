import socket
import threading
import logging
import time

from config import StreamUploaderConfig

class EndOfStreamException(Exception):
    pass


class StreamUploader:
    def __init__(self, imgs, events):
        self.config = StreamUploaderConfig
        self.url = self.config.upload_to
        self.trigger_port = self.config.trigger_port
        self.upload_rate = self.config.upload_rate_per_second
        self.should_upload = threading.Event()
        self.imgs = imgs
        self.events = events

    def handle_trigger(self):
        threading.Thread(target=self._trigger_loop).start()

    def _trigger_loop(self):
        logging.debug('creating trigger socket')
        trigger_socket = self._retry_connection(self.url,
                                                self.trigger_port,
                                                retry_count=30,
                                                backoff_multiplier=3,
                                                max_backoff_seconds=30)
        try:
            logging.info('Trigger socket connected')
            while True:
                logging.debug('waiting for remote trigger')
                self._wait_for_data(trigger_socket, b'send_data')
                logging.debug('Informing trigger server about number of streams')
                trigger_socket.send(str(len(self.imgs)).encode())
                data_start_port = int(trigger_socket.recv(9).decode().strip())
                self.should_upload.set()
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
        with self._retry_connection(self.url, port) as data_socket:
            data_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            logging.debug('Sender connected to port {} preparing to send image {}'.format(port, image_key))
            while self.should_upload.is_set():
                while self.imgs[image_key] is None:
                    time.sleep(0.1)
                logging.debug('Sending image from {} to port {}'.format(image_key, port))
                self.events[image_key].wait()
                self.events[image_key].clear()
                data_socket.sendall(self.imgs[image_key])
                time.sleep(1 / self.upload_rate)

    def _retry_connection(self, url, port, retry_count=5, backoff_multiplier=2, max_backoff_seconds=120):
        backoff = 0.1
        for _ in range(retry_count):
            try:
                s = socket.socket()
                s.connect((url, port))
                return s
            except ConnectionRefusedError as ex:
                logging.debug('Connection to {}:{} refused, trying again in {} seconds'.format(
                    url,
                    port,
                    backoff
                ))
                exception = ex
                time.sleep(backoff)
                backoff = backoff * backoff_multiplier if backoff * backoff_multiplier < max_backoff_seconds else max_backoff_seconds
        raise exception
