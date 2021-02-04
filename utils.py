def get_fileno(fd):
    if hasattr(fd, 'fileno'):
        fd = fd.fileno()
    return fd
