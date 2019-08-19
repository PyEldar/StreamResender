import requests
import threading
import logging
import time


class StreamReader(threading.Thread):
    def __init__(self, url, imgs, *args, **kwargs):
        super().__init__()
        self.url = url
        self._read_event = threading.Event()
        self._stop_event = threading.Event()
        self.imgs = imgs

    def run(self):
        while True:
            logging.debug('{} waiting for read event'.format(self.name))
            while not self._read_event.is_set():
                if self._stop_event.is_set():
                    logging.warning('Stopping thread {}'.format(self.name))
                    return
                time.sleep(0.1)
            r = requests.get(self.url, stream=True, timeout=10, verify=False, auth=('xiaomi', 'camcam'))
            logging.info('Status code of get to {} is {}'.format(r.url, r.status_code))
            if r.status_code == 200:
                self._read_stream(r)
                logging.debug('End of stream from {}'.format(r.url))

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
                self.imgs[self.name] = jpg

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
        self._read_event.clear()
        self.imgs[self.name] = None
        self._stop_event.set()
