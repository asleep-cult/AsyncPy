import sys
import select

class _PollRequest:
    def __init__(self, ident, *, internal_request=None, callback=None):
        self.ident = ident
        self.callback = callback
        self._internal_request = internal_request
        self.result = None


class BasePoller:
    def __init__(self):
        self._read_requests = {}
        self._write_requests = {}

    def _do_poll(self, timeout):
        raise NotImplementedError

    def poll(self, timeout):
        completed_reads, completed_writes = self._do_poll(timeout)

        for request in completed_reads:
            request.callback(request)

        for request in completed_writes:
            request.callback(request)

        return completed_reads, completed_writes

    def add_read(self, *args, **kwargs):
        raise NotImplementedError

    def add_write(self, *args, **kwargs):
        raise NotImplementedError


class SelectorPoller(BasePoller):
    """
    A poller that notifies when a file descriptor is ready for reading/writing
    """
    def _do_poll(self):
        read = list(self._read_requests.values())
        write = list(self._write_requests.values())

        read, write, _ = select.select(read, write, [])
        completed_reads = [self._read_requests.pop(i) for i in read]
        completed_writes = [self._write_requests.pop(i) for i in write]

        return completed_reads, completed_writes

    def add_read(self, ident, callback):
        try:
            ident = ident.fileno()
        except AttributeError:
            pass

        request = _PollRequest(ident, callback=callback)
        self._read_requests[ident] = request

        return request

    def add_write(self, ident, callback):
        try:
            ident = ident.fileno()
        except AttributeError:
            pass

        request = _PollRequest(ident, callback=callback)
        self._write_requests[ident] = request

        return request


if sys.platform in ('linux', 'linux2'):
    import aio

    class AioPoller(BasePoller):
        """
        A poller that notifies when a read/write request has finished
        """
        def _do_poll(self, timeout):
            requests = [
                *self._read_requests.values(),
                *self._write_requests.values()
            ]

            completed_reads = []
            completed_writes = []

            aio.suspend([f._internal_request for r in requests], timeout)

            for request in requests:
                try:
                    request.result = request._internal_request.get_result()
                except BlockingIOError:
                    continue
                completed_reads.append(request)

        def add_read(self, ident, bufsize, callback):
            try:
                ident = ident.fileno()
            except AttributeError:
                pass

            intern = aio.read(ident, bufsize)
            request = _PollRequest(
                ident,
                internal_request=intern,
                callback=callback
            )
            return request

        def add_write(self, ident, data):
            try:
                ident = ident.fileno()
            except AttributeError:
                pass

            intern = aio.write(ident, data)
            request = _PollRequest(
                ident,
                internal_request=intern,
                callback=callback
            )
            return request
