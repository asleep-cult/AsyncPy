def get_fileno(fd):
    try:
        return fd.fileno()
    except AttributeError:
        return fd
