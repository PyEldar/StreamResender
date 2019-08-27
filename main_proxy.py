import time
import logging
import threading

from stream_reader import StreamReader
from stream_uploader import StreamUploader

logging.basicConfig(level=logging.DEBUG)


class MainProxy:
    def __init__(self, stream_urls, upload_url):
        self.stream_urls = stream_urls
        self.imgs = dict()
        self.events = dict()
        self.readers = list()
        self.uploader = StreamUploader(upload_url, trigger_port=8888, imgs=self.imgs, events=self.events)

    def _init_readers(self):
        for i, url in enumerate(self.stream_urls):
            reader = StreamReader(url, self.imgs, events=self.events, name='Reader_' + str(i))
            self.readers.append(reader)
            self.imgs[reader.name] = None
            self.events[reader.name] = threading.Event()
            reader.start()

    def run(self):
        self._init_readers()
        self.uploader.handle_trigger()
        while True:
            try:
                logging.info('Waiting for trigger')
                self.uploader.should_upload.wait()
                logging.info('Starting readers')
                for reader in self.readers:
                    reader.read()
                while self.uploader.should_upload.is_set():
                    time.sleep(1)
                logging.info('Stopping readers')
                for reader in self.readers:
                    reader.stop_reading()
            finally:
                logging.warning('Excepion raised, checking if readers are stopped')
                for reader in self.readers:
                    if reader.is_reading():
                        reader.stop()


if __name__ == '__main__':
    proxy = MainProxy(['https://192.168.1.102:8080/video'], '80.211.218.239')
    proxy.run()
