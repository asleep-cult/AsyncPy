import signal


class SignoHandle:
    def __init__(self, signo):
        self.signo = signo
        self.original = signal.getsignal(signo)
        self.call_original = False
        self.callbacks = []
        signal.signal(signo, self)

    def add(self, callback):
        self.callbacks.append(callback)

    def __call__(self, signo, frame):
        for func in self.callbacks:
            func(signo, frame)

        if self.call_original:
            self.original(signo, frame)


class SignalHub:
    def __init__(self):
        self.sigmap = {}

    def get(self, signo):
        return self.sigmap.get(signo)

    def signal(self, signo, callback, call_original=False):
        handle = self.sigmap.get(signo)
        if handle is None:
            handle = SignoHandle(signo)
            handle.call_original = call_original
        handle.add(callback)

    def poll(self, timeout=0):
        return signal.sigtimedwait(list(self.sigmap), timeout)

    def poll_no_timeout(self):
        return signal.sigwait(list(self.sigmap))


signal_hub = SignalHub()
