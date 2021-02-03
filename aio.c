#include <aio.h>
#include <stdlib.h>
#include <signal.h>
#include <Python.h>

/* TODO: Add signal handler so the process isn't terminated */
/* Fix segfault in Read */

enum AioRequest_Type {
        READ,
        WRITE
};

typedef struct AioRequest {
        PyObject_HEAD;
        int req_type;
        int usable;
        struct aiocb *aiocbp;
} AioRequest;

static PyTypeObject AioRequest_TypeObject = {
        PyVarObject_HEAD_INIT(NULL, 0)
        "AioRequest",
        sizeof(AioRequest)
};

static AioRequest *make_aiorequest()
{
	AioRequest *request;
	request = PyObject_GC_New(AioRequest, &AioRequest_TypeObject);

	request->aiocbp = malloc(sizeof(struct aiocb));
        request->usable = 1;
	request->aiocbp->aio_reqprio = 0;
	request->aiocbp->aio_sigevent.sigev_notify = SIGEV_SIGNAL;
	request->aiocbp->aio_sigevent.sigev_signo = SIGUSR1;
	request->aiocbp->aio_sigevent.sigev_value.sival_ptr = NULL;

	return request;
}

static PyObject *AioRequest_Read(PyObject *self, PyObject *args)
{
        int fd = PyLong_AsLong(PyTuple_GetItem(args, 0));
        int bufsize = PyLong_AsLong(PyTuple_GetItem(args, 1));

        AioRequest *request = make_aiorequest();
        request->req_type = READ;
        request->aiocbp->aio_fildes = fd;
        request->aiocbp->aio_buf = malloc(sizeof(bufsize));
        request->aiocbp->aio_nbytes = bufsize;

        aio_read(request->aiocbp);

        return (PyObject *)request;
}

static PyObject *AioRequest_Write(PyObject *self, PyObject *args)
{
        int fd = PyLong_AsLong(PyTuple_GetItem(args, 0));
        PyObject *bytes = PyTuple_GetItem(args, 1);
        char *buffer = PyBytes_AsString(bytes);
        Py_ssize_t bufsize = PyBytes_Size(bytes);

        AioRequest *request = make_aiorequest();
        request->req_type = WRITE;
        request->aiocbp->aio_fildes = fd;
        request->aiocbp->aio_buf = buffer;
        request->aiocbp->aio_nbytes = bufsize;

        aio_write(request->aiocbp);

        return (PyObject *)request;
}

static PyObject *AioRequest_GetResult(PyObject *self, PyObject *args)
{
        AioRequest *request = (AioRequest *)PyTuple_GetItem(args, 0);

        if (!request->usable) {
                PyErr_SetString(PyExc_ValueError, "Can\'t reuse requests");
                return NULL;
        }
        request->usable = 0;

        if (request->req_type == READ) {
                char *buffer = (char *)request->aiocbp->aio_buf;
                int buflen = request->aiocbp->aio_nbytes;
                PyObject *bytes = PyBytes_FromStringAndSize(buffer, buflen);
                return bytes;
        }

        PyErr_SetString(PyExc_ValueError, "can\'t do that yet");
        return NULL;
}

static PyMethodDef aiomethods[] = {
        {"read",  AioRequest_Read, METH_VARARGS, NULL},
        {"write", AioRequest_Write, METH_VARARGS, NULL},
        {"get_result", AioRequest_GetResult, METH_VARARGS, NULL},
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
    return PyModule_Create(&aiomodule);
}
