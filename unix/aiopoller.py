import aio
import signal

from ..base_pollers import IOPollerBase, IOPollerSubmission, MuxHibrenatePoller
from ..utils import get_fileno

IO_SIGNAL = signal.SIGUSR1


class AioPoller(IOPollerBase):
    def _check_submissions(self, submissions):
        completed = []

        for submission in submissions:
            submission.times_polled += 1
            try:
                result = submission.internal.get_result()
            except BlockingIOError:
                continue

            submission.call_callbacks(result)
            completed.append(submission)

        return completed

    def poll(self, timeout=0):
        submissions = [*self._reads.values(), *self._writes.values()]

        if timeout != 0:
            internal_requests = [s.internal for s in submissions]
            aio.suspend(internal_requests, timeout)

        reads = self._check_submissions(self._reads)
        writes = self._check_submissions(self._writes)
        return reads, writes

    # TODO: Expose fd and req_type in aio.c
    def submit(self, fd, request_type, aio_request, callbacks=None):
        fd = get_fileno(fd)
        submission = IOPollerSubmission(
            fd, callbacks=callbacks, internal=aio_request
        )

        if request_type == 0:
            self._reads[fd] = submission
        elif request_type == 1:
            self._writes[fd] = submission

        return submission

    def read(self, fd, bufsize, callbacks):
        fd = get_fileno(fd)
        request = aio.read(fd, bufsize)
        submission = self.submit(fd, 0, request, callbacks)
        return submission

    def write(self, fd, data, callbacks):
        fd = get_fileno(fd)
        request = aio.write(fd, data)
        submission = self.submit(fd, 1, request, callbacks)
        return submission


class AioHibrenatePoller(MuxHibrenatePoller):
    def poll(self):
        self.awake = False
        signal.sigwait(IO_SIGNAL)
        self.awake = True

    def wakeup(self):
        signal.raise_signal(IO_SIGNAL)
