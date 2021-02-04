import select

from .utils import get_fileno


class ReactorRequest:
    def __init__(self, fd, callback=None):
        self.fd = fd
        self.callback = callback
        self.result = None


class SelectReactor:
    def __init__(self):
        self._read_requests = {}
        self._write_requests = {}

    def submit_read(self, fd, callback=None):
        fd = get_fileno(fd)
        request = ReactorRequest(fd, callback)
        self._read_requests[fd] = request
        return request

    def submit_write(self, fd, callback=None):
        fd = get_fileno(fd)
        request = ReactorRequest(fd, callback)
        self._write_requests[fd] = request
        return request

    def poll(self, timeout=0):
        reads, writes, _ = select.select(
            list(self._read_requests),
            list(self._write_requests),
            [],
            timeout=timeout
        )
        reads = [self._read_requests[fd] for fd in reads]
        writes = [self._write_requests[fd] for fd in writes]

        return reads, writes
