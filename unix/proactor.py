import aio

from ..utils import get_fileno


class ProactorRequest:
    def __init__(self, fd, internal_request, callback=None):
        self.fd = fd
        self.internal_request = internal_request
        self.callback = None
        self.result = None


class AioProactor:
    def __init__(self):
        self._read_requests = {}
        self._write_requests = {}

    def submit_read(self, fd, bufsize, callback=None):
        fd = get_fileno(fd)
        internal_request = aio.read(fd, bufsize)
        request = ProactorRequest(fd, internal_request, callback)
        self._read_requests[fd] = request
        return request

    def submit_write(self, fd, data, callback=None):
        fd = get_fileno(fd)
        internal_request = aio.write(fd, bytes(data))
        request = ProactorRequest(fd, internal_request, callback)
        self._write_requests[fd] = request
        return request

    def _check_reads(self):
        completed = []

        for request in self._read_requests.items():
            try:
                request.result = request.internal_request.get_result()
            except BlockingIOError:
                continue

            if request.callback is not None:
                request.callback(request)

            completed.append(request)

        return completed

    def _check_writes(self):
        completed = []

        for request in self._write_requests.items():
            try:
                request.result = request.internal_request.get_result()
            except BlockingIOError:
                continue

            if request.callback is not None:
                request.callback(request)

            completed.append(request)

        return completed


    def poll(self, timeout=0):
        requests = [
            *self._read_requests.items(),
            *self._write_requests.items()
        ]

        aio.suspend([r.internal_request for r in requests], timeout)

        return self._check_reads(), self._check_writes()
