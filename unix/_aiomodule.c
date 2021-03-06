#include <aio.h>
#include <stdlib.h>
#include <signal.h>
#include <Python.h>

enum AioRequest_Type {
        READ,
        WRITE
};

typedef struct AioRequest {
        PyObject_HEAD;
        int fd;
        int req_type;
        struct aiocb *aiocbp;
} AioRequest;

static PyObject *AioRequest_GetResult(PyObject *self, PyObject *args);
static PyObject *AioRequest_Cancel(PyObject *self, PyObject *args);
static PyObject *AioRequest_Fileno(PyObject *self, PyObject *args);
static PyObject *AioRequest_Reqtype(PyObject *self, PyObject *args);
static void AioRequest_Dealloc(AioRequest *self);

static PyMethodDef AioRequest_Methods[] = {
        {"get_result", AioRequest_GetResult, METH_VARARGS, NULL},
        {"cancel", AioRequest_Cancel, METH_VARARGS, NULL},
        {"fileno", AioRequest_Fileno, METH_VARARGS, NULL},
        {"req_type", AioRequest_Reqtype, METH_VARARGS, NULL},
        {NULL, NULL, 0, NULL}        /* Sentinel */
};

static PyTypeObject AioRequest_TypeObject = {
        PyVarObject_HEAD_INIT(NULL, 0)
        .tp_name = "aio.AioRequest",
        .tp_basicsize = sizeof(AioRequest),
        .tp_itemsize = 0,
        .tp_methods = AioRequest_Methods,
        .tp_flags = Py_TPFLAGS_DEFAULT,
        .tp_new = PyType_GenericNew,
        .tp_dealloc = (destructor)AioRequest_Dealloc
};

static AioRequest *make_aiorequest(int fd)
{
        AioRequest *request;
        request = PyObject_New(AioRequest, &AioRequest_TypeObject);
        request->fd = fd;
        request->aiocbp = malloc(sizeof(struct aiocb));
        request->aiocbp->aio_reqprio = 0;
        request->aiocbp->aio_fildes = fd;
        request->aiocbp->aio_sigevent.sigev_notify = SIGEV_SIGNAL;
        request->aiocbp->aio_sigevent.sigev_signo = SIGUSR1;
        request->aiocbp->aio_sigevent.sigev_value.sival_ptr = request;

        return request;
}

static PyObject *AioRequest_Read(PyObject *self, PyObject *args)
{
        int fd = PyLong_AsLong(PyTuple_GetItem(args, 0));
        int bufsize = PyLong_AsLong(PyTuple_GetItem(args, 1));

        AioRequest *request = make_aiorequest(fd);
        request->req_type = READ;
        request->aiocbp->aio_buf = malloc(sizeof(bufsize));
        request->aiocbp->aio_nbytes = bufsize;

        int status = aio_read(request->aiocbp);

        if (status == -1) {
                PyErr_SetFromErrno(PyExc_OSError);
                return NULL;
        }

        return (PyObject *)request;
}

static PyObject *AioRequest_Write(PyObject *self, PyObject *args)
{
        int fd = PyLong_AsLong(PyTuple_GetItem(args, 0));
        PyObject *bytes = PyTuple_GetItem(args, 1);
        char *buffer = PyBytes_AsString(bytes);
        Py_ssize_t bufsize = PyBytes_Size(bytes);

        AioRequest *request = make_aiorequest(fd);
        request->req_type = WRITE;
        request->aiocbp->aio_buf = buffer;
        request->aiocbp->aio_nbytes = bufsize;

        int status = aio_write(request->aiocbp);

        if (status == -1) {
                PyErr_SetFromErrno(PyExc_OSError);
                return NULL;
        }

        return (PyObject *)request;
}

static PyObject *AioRequest_GetResult(PyObject *self, PyObject *args)
{
        AioRequest *request = (AioRequest *)self;

        int status = aio_error(request->aiocbp);
        if (status != 0) {
                if (status == EINPROGRESS) {
                        PyErr_SetString(
                                PyExc_BlockingIOError,
                                "Can't get result from unsinished request");
                }
                else if (status == ECANCELED) {
                        PyErr_SetString(
                                PyExc_OSError,
                                "Can't get result from cancelled request");
                }
                else {
                        PyErr_SetFromErrno(PyExc_OSError);
                }
                return NULL;
        }

        int ret = aio_return(request->aiocbp);

        if (ret == -1) {
                PyErr_SetFromErrno(PyExc_OSError);
                return NULL;
        }

        if (request->req_type == READ) {
                char *buffer = (char *)request->aiocbp->aio_buf;
                PyObject *bytes = PyBytes_FromStringAndSize(buffer, ret);
                return bytes;
        }
        return PyLong_FromLong(ret);
}

static PyObject *AioRequest_Cancel(PyObject *self, PyObject *args)
{
        AioRequest *request = (AioRequest *)self;

        int status = aio_cancel(request->fd, request->aiocbp);

        if (status != AIO_CANCELED) {
                if (status == AIO_NOTCANCELED) {
                        PyErr_SetString(
                                PyExc_OSError,
                                "Failed to cancel request");
                }
                else if (status == AIO_ALLDONE) {
                        PyErr_SetString(
                                PyExc_OSError,
                                "The request is already finished");
                }
                else {
                        PyErr_SetFromErrno(PyExc_OSError);
                }
                return NULL;
        }
        Py_RETURN_NONE;
}

static PyObject *AioRequest_Fileno(PyObject *self, PyObject *args)
{
        AioRequest *request = (AioRequest *)self;
        return PyLong_FromLong(request->fd);
}

static PyObject *AioRequest_Reqtype(PyObject *self, PyObject *args)
{
        AioRequest *request = (AioRequest *)self;
        return PyLong_FromLong(request->req_type);
}

static void AioRequest_Dealloc(AioRequest *self)
{
        if (self->req_type == READ) {
            free((void *)self->aiocbp->aio_buf);
        }
        free(self->aiocbp);
        PyTypeObject *tp = Py_TYPE(self);
        tp->tp_free(self);
}

static PyObject *Aio_Suspend(PyObject *self, PyObject *args)
{
        PyObject *requests = PyTuple_GetItem(args, 0);
        long nanoseconds = PyLong_AsLong(PyTuple_GetItem(args, 1));

        struct timespec *timeout;
        if (nanoseconds == 0) {
                struct timespec timeout_;
                timeout_.tv_sec = 0;
                timeout_.tv_nsec = nanoseconds;
                timeout = &timeout_;
        }
        else {
                timeout = NULL;
        }

        int length = PyList_Size(requests);
        const struct aiocb *aiocb_list[length];

        for (int i = 0; i < length; i++) {
                AioRequest *request = (AioRequest *)PyList_GetItem(
                                                                requests, i);
                aiocb_list[i] = (const struct aiocb *)request->aiocbp;
        }

        int status;
        Py_BEGIN_ALLOW_THREADS;
        /* Release the GIL so threads aren't waiting on us doing nothing */
        status = aio_suspend(
                        (const struct aiocb **const)aiocb_list,
                        length,
                        timeout);
        Py_END_ALLOW_THREADS;

        if (status == -1) {
                PyErr_SetFromErrno(PyExc_OSError);
                return NULL;
        }
        Py_RETURN_NONE;
}

static PyMethodDef aiomethods[] = {
        {"read",  AioRequest_Read, METH_VARARGS, NULL},
        {"write", AioRequest_Write, METH_VARARGS, NULL},
        {"suspend", Aio_Suspend, METH_VARARGS, NULL},
        {NULL, NULL, 0, NULL}        /* Sentinel */
};

static struct PyModuleDef aiomodule = {
        PyModuleDef_HEAD_INIT,
        "aio",
        NULL,
        -1,
        aiomethods
};

PyMODINIT_FUNC
PyInit_aio(void)
{
        PyObject *module = PyModule_Create(&aiomodule);
        PyTypeObject *object = &AioRequest_TypeObject;
        if (PyType_Ready(object) < 0) {
                return NULL;
        }
        Py_INCREF(object);
        int status = PyModule_AddObject(
                module,
                "AioRequest",
                (PyObject *)object);
        if (status < 0) {
                return NULL;
        }
        return module;
}
