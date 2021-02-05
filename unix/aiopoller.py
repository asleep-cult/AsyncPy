from . import aio
import signal

from ..base_pollers import IOPollerBase, MuxHibernatePoller
from ..utils import get_fileno
from .signals import signal_hub

WAKEUP_SIGNAL = signal.SIGUSR1
READ = 0
WRITE = 1


class AioRequest:
    def __init__(self, internal, callbacks=None):
        self.internal = internal
        self.result = None
        self.callbacks = callbacks or []

    def add_callback(self, callback):
        self.callbacks.append(callback)

    def call_callbacks(self):
        for callback in self.callbacks:
            callback()


class AioPollerSubmission:
    def __init__(self, fd):
        self.fd = fd
        self.requests = []

    def add_request(self, request):
        self.requests.append(request)

    def __repr__(self):
        return \
            'AioPollerSubmission(fd=%s, outstanding_requessts=%s)' % (
                self.fd,
                len(self.requests)
            )


class AioPoller(IOPollerBase):
    @property
    def requests(self):
        requests = []
        for read in self._reads.values():
            requests.extend(read.requests)
        for write in self._writes.values():
            requests.extend(write.requests)

    def _check_submissions(self, submissions):
        completed = []
        for submission in submissions:
            for request in submissions.requests:
                try:
                    request.result = request.get_result()
                except BlockingIOError:
                    continue

                submission.requests.remove(request)
                completed.append(request)
        return completed

    def submit(self, request, callbacks=None):
        req_type = request.req_type()
        fd = request.fileno()
        submissions = self._reads if req_type == READ else self._writes
        submission = submissions.get(fd)
        if submission is None:
            submission = AioPollerSubmission(fd)
        request = AioRequest(request, callbacks)
        submission.add_request(request)
        return request

    def read(self, fd, bufsize, callbacks=None):
        fd = get_fileno(fd)
        request = self.submit(aio.read(fd, bufsize), callbacks)
        return request

    def write(self, fd, data, callbacks=None):
        fd = get_fileno(fd)
        request = self.submit(aio.write(fd, data), callbacks)
        return request

    def poll(self, timeout=0):
        if timeout != 0:
            internal = [r.internal for r in self.requests]
            aio.suspend(internal, timeout)

        reads = self._check_submissions(self._reads.values())
        writes = self._check_submissions(self._writes.values())
        return reads, writes


class AioHibernatePoller(MuxHibernatePoller):
    def poll(self):
        self.awake = False
        signal_hub.poll_no_timeout()
        self.awake = True

    def wakeup(self):
        signal.raise_signal(WAKEUP_SIGNAL)
