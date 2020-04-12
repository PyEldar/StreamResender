class MainProxyConfig:
    streams = [
        {'url': 'https://192.168.43.170:8080/video', 'auth': ('xiaomi', 'camcam')},
        {'url': 'https://192.168.43.112:8080/video', 'auth': ('xiaomi', 'camcam')}
    ]


class StreamUploaderConfig:
    upload_to = '80.211.218.239'
    trigger_port = 8888
    upload_rate_per_second = 3
