import socket
import signal
from asyncpy.mux import Mux
from asyncpy.unix.aiopoller import AioPoller, AioHibernatePoller
from asyncpy.unix.signals import signal_hub

mux = Mux(AioPoller, AioHibernatePoller)

signal_hub.signal(signal.SIGUSR1, lambda *args: None)
signal_hub.signal(exit)


def write_callback(length):
    assert length == 11
    print('Write Complete')


def read_callback(data):
    assert data == b'hello world'
    print('Read Complete')


a, b = socket.socketpair()

for i in range(2000):  # TODO: fix OSError: 0???
    print(i)
    mux.iopoller.write(a.fileno(), b'hello world', [write_callback])
    mux.iopoller.read(b.fileno(), 11, [read_callback])

print('Started')
mux.run()
