import aio
import signal

from ..base_pollers import IOPollerBase, IOPollerSubmission, MuxHibrenatePoller
from ..utils import get_fileno

IO_SIGNAL = signal.SIGUSR1
READ = 0
WRITE = 1


class AioPoller(IOPollerBase):
    def _check_submissions(self, submissions):
        completed = []

        for submission in submissions:
            submission.times_polled += 1
            try:
                result = submission.internal.get_result()
            except BlockingIOError:
                continue

            submission.call_callbacks(self.mux, result)
            completed.append(submission)

        return completed

    def poll(self, timeout=0):
        if timeout != 0:
            internal_requests = \
                [s.internal for s in self._reads.values()] + \
                [s.internal for s in self._writes.values()]
            aio.suspend(internal_requests, timeout)

        reads = self._check_submissions(self._reads)
        writes = self._check_submissions(self._writes)
        return reads, writes

    def submit(self, aio_request, callbacks=None):
        fd = aio_request.fileno()
        request_type = aio_request.req_type()
        submission = IOPollerSubmission(
            fd, callbacks=callbacks, internal=aio_request
        )

        if request_type == READ:
            self._reads[fd] = submission
        elif request_type == WRITE:
            self._writes[fd] = submission

        return submission

    def read(self, fd, bufsize, callbacks):
        fd = get_fileno(fd)
        request = aio.read(fd, bufsize)
        submission = self.submit(request, callbacks)
        return submission

    def write(self, fd, data, callbacks):
        fd = get_fileno(fd)
        request = aio.write(fd, data)
        submission = self.submit(request, callbacks)
        return submission


class AioHibrenatePoller(MuxHibrenatePoller):
    def poll(self):
        self.awake = False
        signal.sigwait(IO_SIGNAL)
        self.awake = True

    def wakeup(self):
        signal.raise_signal(IO_SIGNAL)