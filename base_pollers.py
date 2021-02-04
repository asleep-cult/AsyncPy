import functools


class IOPollerSubmission:
    """
    A submission to an I/O poller.
    """
    def __init__(self, ident, callbacks=None, internal=None, window=None):
        self.ident = ident
        self.callbacks = callbacks
        self.internal = internal
        self.times_polled = 0
        self.window = window

    def call_callbacks(self, mux, *args, **kwargs):
        for callback in self.callbacks:
            callback = functools.partial(callback, *args, **kwargs)
            mux.add_pending_call(callback)

    def __repr__(self):
        return \
            f'<IOPollerSubmission ident={self.ident}, ' \
            f'callbacks={self.callbacks}, window={self.window}, ' \
            f'times_polled={self.times_polled}>'


class IOPollerBase:
    """
    A "selector" that polls fds and asynchronous kernel requests
    for ready-ness, the poll function must not block with a timeout of 0.
    """
    def __init__(self, mux):
        self.mux = mux
        self._reads = {}
        self._writes = {}

    @property
    def reads(self):
        return dict(self._reads)

    @property
    def writes(self):
        return dict(self._writes)

    def poll(self, timeout=0):
        raise NotImplementedError

    def submit(self, *args, **kwargs):
        raise NotImplementedError

    def read(self, *args, **kwargs):
        raise NotImplementedError

    def write(self, *args, **kwargs):
        raise NotImplementedError

    def __repr__(self):
        return \
            f'<{self.__class__.__name__} ' \
            f'outstanding_reads={len(self._reads)}, ' \
            f'outstanding_writes={len(self._writes)}>'


class MuxHibernatePoller:
    def __init__(self, mux):
        """
        A poller that puts a Multiplexer into an interruptable hibernating
        state.
        """
        self.mux = mux
        self.awake = True

    def poll(self):
        raise NotImplementedError

    def wakeup(self):
        raise NotImplementedError

    def __repr__(self):
        return f'<{self.__class__.__name__} awake={self.awake}>'
