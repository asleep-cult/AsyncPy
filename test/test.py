import socket
import signal
import os
from asyncpy.mux import Mux
from asyncpy.unix.aiopoller import AioPoller, AioHibernatePoller
from asyncpy.unix.signals import signal_hub

signal_hub.signal(signal.SIGUSR1, lambda *args: print('Got Signal'))
signal_hub.signal(signal.SIGINT, lambda signum, _: os.kill(os.getpid(), signum))
print(signal_hub.sigmap)

mux = Mux(AioPoller, AioHibernatePoller)

a, b = socket.socketpair()
for _ in range(200):
	mux.iopoller.write(a.fileno(), b'askldjaklsdjaklsjd', [lambda *args: print('Completed Write')])
	mux.iopoller.read(b.fileno(), 10, [lambda *args: print(args)])

mux.run()
