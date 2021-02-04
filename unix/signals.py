import signal
import warnings

attached = False

class SigHandler:
    def __init__(self, signo):
        self.signo = signo
        self.original = signal.getsignal(signo)
        self.funcs = []
        self.call_original = True
        self.attached = False

    def clear(self):
        self.funcs.clear()

    def remove(func):
        self.funcs.remove(func)

    def add(func):
        self.funcs.append(func)
        if not self.attached:
            warnings.warn(
                RuntimeWarning,
                "Adding to detached signal handler %r" % self
            )

    def detach(self):
        self.attached = True
        signal.signal(self.signo, self.original)

    def attach(self):
        self.attached = False
        signal.signal(self.signo, self)

    def __call__(self, signum, frame):
        if self.call_original:
            self.original(signum, frame)
        for func in self.funcs:
            func(signum, frame)


class SigReceiver:
    def __init__(self):
        self._handlers = {}

    def get_handler(self, signo):
        return self._handlers.get(signo, None)

    def signal(self, signo, func):
        handler = self.get_handler(signo)
        if handler is not None:
            handler = SigHandler(signo)
        handler.add(func)
        return handler

    def attach(self):
        global attached
        attached = True

        for handler in self._handlers.values():
            handler.attach()

    def detach(self):
        global attached
        attached = False

        for handler in self._handlers.values():
            handler.detach()

    def poll(self, timeout=0):
        if timeout == 0:
            return signal.sigwaitinfo(list(self._handlers))
        return signal.sigtimedwait(list(self._handlers), timeout)
