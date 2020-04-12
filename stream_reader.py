import requests
import threading
import logging
import time


class StreamReader(threading.Thread):
    def __init__(self, url, imgs, events, auth=None, *args, **kwargs):
        super().__init__()
        self.auth = auth
        self.url = url
        self._read_event = threading.Event()
        self._stop_event = threading.Event()
        self.imgs = imgs
        self.events = events

    def run(self):
        while not self._stop_event.is_set():
            try:
                logging.debug('{} waiting for read event'.format(self.name))
                while not self._read_event.is_set():
                    if self._stop_event.is_set():
                        logging.warning('Stopping thread {}'.format(self.name))
                        return
                    time.sleep(0.1)
                r = requests.get(self.url, stream=True, timeout=10, verify=False, auth=self.auth)
                logging.info('Status code of get to {} is {}'.format(r.url, r.status_code))
                if r.status_code == 200:
                    self._read_stream(r)
                    logging.debug('End of stream from {}'.format(r.url))
            except requests.exceptions.ConnectionError:
                logging.exception('Reader connection error')
                time.sleep(0.1)
                continue
            finally:
                self.imgs[self.name] = None

    def _read_stream(self, request):
        bytes_array = bytes()
        for chunk in request.iter_content(chunk_size=1024):
            if not self._read_event.is_set():
                request.connection.close()
                break
            bytes_array += chunk
            a = bytes_array.find(b'\xff\xd8')
            b = bytes_array.find(b'\xff\xd9')
            if a != -1 and b != -1:
                jpg = bytes_array[a:b + 2]
                bytes_array = bytes_array[b + 2:]
                logging.debug('Read one')
                self.imgs[self.name] = jpg
                self.events[self.name].set()

    def read(self):
        if not self.is_alive():
            self.start()
        self._read_event.set()

    def stop_reading(self):
        self.imgs[self.name] = None
        self._read_event.clear()

    def is_reading(self):
        return self._read_event.is_set()

    def stop(self):
        self.stop_reading()
        self._stop_event.set()
