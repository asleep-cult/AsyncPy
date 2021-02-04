import socket
import signal
from asyncpy.mux import Mux
from asyncpy.unix.aiopoller import AioPoller, AioHibrenatePoller
from asyncpy.unix.signals import signal_hub

signal_hub.signal(signal.SIGUSR1, lambda *args: print('Got Signal'))
signal_hub.signal(signal.SIGINT, lambda *args: exit())
print(signal_hub.sigmap)

mux = Mux(AioPoller, AioHibrenatePoller) 

a, b = socket.socketpair()
mux.iopoller.write(a.fileno(), b'askldjaklsdjaklsjd', [lambda *args: print('Completed Write')])
mux.iopoller.read(b.fileno(), 10, [lambda *args: print(args)])

mux.run()
