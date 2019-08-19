# StreamResender
A local network client which gathers video streams from local network and uploads them to remote server

# Local Streaming
HTTP MJPEG stream (multipart/x-mixed-replace mimetype) is supported with HTTP basic authentication

# Stream upload
Single persistent connection is established with remote server which send triggers to start streaming from local network
Client tells remote server how many sockets to open and then single local stream is bridged to remote socket

# Usage
