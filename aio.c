#include <aio.h>
#include <stdlib.h>
#include <signal.h>
#include <Python.h>

enum AioRequest_Type = {
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
        PyVarObject_HEAD_INIT(NULL, 0),
        "AioRequest"
        sizeof(AioRequest)
};

static PyObject *make_aiorequest(struct aiocb *aiocbp)
{
        AioRequest *req;
        PyObject *object = PyObject_GC_New(req, &AioRequest_TypeObject);
        (AioRequest *)object->usable = 1;
        return req;
}

static PyObject *AioRequest_Read(PyObject *self, PyObject *args)
{
        int fd = PyLong_AsLong(PyTuple_GetItem(args, 0));
        int bufsize = PyLong_AsLong(PyTuple_GetItem(args, 1));
        struct aiocb *aiocbp = malloc(sizeof(struct aiocb));
        aiocbp->aio_filedes = fd;
        aiocbp->aio_buf = malloc(sizeof(bufsize));
        aiocbp->aio_nbytes = bufsize;
        aiocbp->aio_reqprio = 0;
        aiocbp->aio_sigevent.sigev_notify = SIGEV_SIGNAL;
        aiocbp->aio_sigevent.sigev_signo = IO_SIGNAL;
        aiocbp->aio_sigevent.sigev_value.sival_ptr = NULL;
        aio_read(aiocbp);
        return make_aiorequest(aiocbp);
}

static PyObject *AioRequest_Write(PyObject *self, PyObject *args)
{
        int fd = PyLong_AsLong(PyTuple_GetItem(args, 0));
        PyObject *bytes = PyTuple_GetItem(args, 1);
        char *buffer = PyBytes_AsString(bytes);
        Py_ssize_t bufsize = PyBytes_Size(bytes);
        struct aiocb *aiocbp = malloc(sizeof(struct aiocb));
        aiocbp->aio_filedes = fd;
        aiocbp->aio_buf = buffer;
        aiocbp->aio_nbytes = bufsize;
        aiocbp->aio_reqprio = 0;
        aiocbp->aio_sigevent.sigev_notify = SIGEV_SIGNAL;
        aiocbp->aio_sigevent.sigev_signo = IO_SIGNAL;
        aiocbp->aio_sigevent.sigev_value.sival_ptr = NULL;
        return make_aiorequest(aiocbp);
}

static PyObject *AioRequest_GetResult(PyObject *self, PyObject *args)
{
        AioRequest *req = (AioRequest *)PyTuple_GetItem(args, 0);
        if (!req->usable) {
                PyErr_SetString(PyExc_ValueError, "Can\'t reuse requests");
        }
        req->usable = 0;
        if (rep->req_type == READ) {
                char *buffer = req->aiocbp->aio_buf;
                int buflen = req->aiocbp->aio_nbytes;
                char *bytes = PyBytes_FromStringAndSize(buffer);
                free(buffer);
                free(req->aiocbp);
                return bytes;
        }
        Py_RETURN_NONE;
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
