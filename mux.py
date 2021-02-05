import collections


class Mux:
    def __init__(self, iopoller, hpoller):
        self.iopoller = iopoller(self)
        self.hpoller = hpoller(self)
        self.pending_calls = collections.deque()

    def add_pending_call(self, callback):
        self.pending_calls.append(callback)
        self.hpoller.wakeup()

    def run(self):
        while True:
            if not self.pending_calls:
                self.hpoller.poll()

            if self.pending_calls:
                callback = self.pending_calls.popleft()
                callback()

            self.iopoller.poll(0)

    def __repr__(self):
        return \
            f'<Mux iopoller={self.iopoller!r}, ' \
            f'hpoller={self.hpoller!r}>'
