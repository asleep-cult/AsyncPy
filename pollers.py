import sys
import select


class PollArg:
    def __init__(self, arg, callback):
        self.arg = arg
        self.callback = callback

    def __repr__(self):
        return '<%s arg=%r, callback=%r>' % (
            self.__class__.__name__,
            self.arg,
            self.callback)


class SelectorPoller:
    def __init__(self):
        self._read_args = {}
        self._write_args = {}

    def add_read(self, fd, callback):
        if hasattr(fd, 'fileno'):
            fd = fd.fileno()
        self._read_args[fd] = arg = PollArg(fd, callback)
        return arg

    def add_write(self, fd, callback):
        if hasattr(fd, 'fileno'):
            fd = fd.fileno()
        self._write_args[fd] = arg = PollArg(fd, callback)
        return arg

    def poll(self, timeout=0):
        read, write, _ = select.select(
            list(self._read_fds),
            list(self._write_fds),
            [],
            timeout)
        read = [self._read_args[fd] for fd in read]
        write = [self._write_args[fd] for fd in write]

        for arg in read:
            arg.callback()

        for arg in write:
            arg.callback()

        return read, write
