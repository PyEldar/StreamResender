import time
import logging
import threading

from stream_reader import StreamReader
from stream_uploader import StreamUploader
from config import MainProxyConfig

logging.basicConfig(level=logging.DEBUG)


class MainProxy:
    def __init__(self):
        self.config = MainProxyConfig
        self.imgs = dict()
        self.events = dict()
        self.readers = list()
        self.uploader = StreamUploader(imgs=self.imgs, events=self.events)

    def _init_readers(self):
        for i, stream in enumerate(self.config.streams):
            reader = StreamReader(stream['url'], self.imgs, events=self.events, name='Reader_' + str(i), auth=stream.get('auth'))
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
    proxy = MainProxy()
    proxy.run()
