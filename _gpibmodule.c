/*
 * Copyright (C) 2008 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/***********************************************************
 * Python wrapper module for gpib library functions.
 * vim:ts=4:sw=4:softtabstop=0:smarttab
 ************************************************************/


#include "Python.h"

#ifdef USE_INES
#include <ugpib.h>
#else
#include <gpib/ib.h>
#endif

#include <lockdev.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>


#define LOCKNAME_SIZE 32


/*
struct _iberr_string {
    int code;
    char *meaning;
} _iberr_string;

static struct _iberr_string GPIB_errors[] = {
    {EDVR, "A system call has failed. ibcnt/ibcntl will be set to the value of errno."},
    {ECIC, "Your interface board needs to be controller-in-charge, but is not."},
    {ENOL, "You have attempted to write data or command bytes, but there are no listeners currently addressed."},
    {EADR, "The interface board has failed to address itself properly before starting an io operation."},
    {EARG, "One or more arguments to the function call were invalid."},
    {ESAC, "The interface board needs to be system controller, but is not."},
    {EABO, "A read or write of data bytes has been aborted, possibly due to a timeout or reception of a device clear command."},
    {ENEB, "The GPIB interface board does not exist, its driver is not loaded, or it is not configured properly."},
    {EDMA, "Not used (DMA error), included for compatibility purposes."},
    {EOIP, "Function call can not proceed due to an asynchronous IO operation (ibrda(), ibwrta(), or ibcmda()) in progress."},
    {ECAP, "Incapable of executing function call, due the GPIB board lacking the capability, or the capability being disabled in software."},
    {EFSO, "File system error. ibcnt/ibcntl will be set to the value of errno."},
    {EBUS, "An attempt to write command bytes to the bus has timed out."},
    {ESTB, "One or more serial poll status bytes have been lost. This can occur due to too many status bytes accumulating (through automatic serial polling) without being read."},
    {ESRQ, "The serial poll request service line is stuck on."},
    {ETAB, "This error can be returned by ibevent(), FindLstn(), or FindRQS(). See their descriptions for more information."},
    {0, NULL},
};
*/

static PyObject *GpibError;

/* ----------------------------------------------------- */

int get_lockname(char *buffer, size_t size, int descriptor) { 
	int minor;

	memset(buffer, 0, size);
	ibask(descriptor, IbaBNA, &minor);
	return snprintf(buffer, size, "/dev/gpib%d", minor);
}

static char gpib_find__doc__[] =
""
;

static PyObject* gpib_find(PyObject *self, PyObject *args)
{
    char *name;
	int ud;
	char lockname[LOCKNAME_SIZE];
	pid_t owner;

	if (!PyArg_ParseTuple(args, "s", &name))
		return NULL;

	if((ud = ibfind(name)) & ERR){
	  PyErr_SetString(GpibError,"Find Error: can't find device!");
	  return NULL;
	}

	get_lockname(lockname, LOCKNAME_SIZE, ud);

    if ((owner = dev_lock(lockname)) != 0) {
	  ibonl(ud, 0);
	  if (owner < 0) {
	  	PyErr_SetFromErrno(PyExc_OSError);
	  } else {
	  	PyErr_Format(GpibError, "Find Error: locked by: %d.", owner);
	  }
	  return NULL;
	}
	return Py_BuildValue("i", ud);
}

static char gpib_ibdev__doc__[] =
"ibdev -- get a device handle]\n"
"ibdev(boardid, pad, [sad, timeout, eot, eoc])"
;

static PyObject* gpib_ibdev(PyObject *self, PyObject *args)
{
    int ud = -1;
    int board = 0;
    int pad = 0;
    int sad = 0;
    int tmo = 14;
    int eot = 1;
    int flags = 0x1000;
    char eoc = 0xa;
    char *errstr;

	if (!PyArg_ParseTuple(args, "ii|iiic", &board, &pad, &sad, &tmo, &eot, &eoc))
		return NULL;
    ud = ibdev(board, pad, sad, tmo, eot, flags | eoc);
// int ibdev(int boardID, int pad, int sad, int tmo, int eot, int eos);
    if (ud < 0) {
		errstr = PyMem_Malloc(64);
		snprintf(errstr, 64, "ibdev failed: iberr: %d", iberr);
		PyErr_SetString(GpibError, errstr);
		PyMem_Free(errstr);
        return NULL;
    }
	return Py_BuildValue("i", ud);
}


static char gpib_ibask__doc__[] =
"ibask -- query configuration (board or device)";

static PyObject* gpib_ibask(PyObject *self, PyObject *args)
{
	int device;
	int option;
	int result;

	if (!PyArg_ParseTuple(args, "ii",&device, &option))
		return NULL;

    if (ibask(device, option, &result) & ERR) {
	  PyErr_SetString(GpibError, "Error: ibask");
      return NULL;
    }

	return Py_BuildValue("i", result);
}


static char gpib_ibconfig__doc__[] =
"ibconfig -- change configuration (board or device)" ;

static PyObject* gpib_ibconfig(PyObject *self, PyObject *args)
{
    int device;
    int option;
    int setting;

	if (!PyArg_ParseTuple(args, "iii",&device, &option, &setting))
		return NULL;

    if (ibconfig(device, option, setting) & ERR) {
	  PyErr_SetString(GpibError, "Config Error: ibconfig");
	  return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}


static char gpib_read__doc__[] =
""
;

static PyObject* gpib_read(PyObject *self, PyObject *args)
{
	char *result;
	char *errstr;
	int device;
	int len;
	PyObject *retval;

	if (!PyArg_ParseTuple(args, "ii",&device,&len))
		return NULL;

	result = PyMem_Malloc(len + 1);
	if(result == NULL)
	{
		PyErr_SetString(GpibError,"Read Error: can't get Memory ");
		return NULL;
	}

	if( ibrd(device,result,len) & ERR )
	{
		errstr = PyMem_Malloc(4096);
		snprintf(errstr, 4096, "Read Error: ibrd() failed: iberr: %d", iberr);
		PyErr_SetString(GpibError, errstr);
		PyMem_Free(errstr);
		PyMem_Free(result);
		return NULL;
	}
	result[ibcnt] = '\0';

	retval = Py_BuildValue("s", result);
	PyMem_Free(result);
	return retval;
}

static char gpib_readbin__doc__[] =
""
;


static PyObject* gpib_readbin(PyObject *self, PyObject *args)
{
	char *result;
	char *errstr;
	PyObject *retval;
	int device;
	int len;

	if (!PyArg_ParseTuple(args, "ii",&device,&len))
		return NULL;

	result = PyMem_Malloc(len + 1);
	if(result == NULL)
	{
		PyErr_SetString(GpibError,"Read Error: can't get Memory ");
		return NULL;
	}

	if( ibrd(device,result,len) & ERR )
	{
		errstr = PyMem_Malloc(4096);
		snprintf(errstr, 4096, "Read Error: ibrd() failed: iberr: %d", iberr);
		PyErr_SetString(GpibError, errstr);
		PyMem_Free(errstr);
		PyMem_Free(result);
		return NULL;
	}

	retval = Py_BuildValue("s#", result, ibcnt);
	PyMem_Free(result);
	return retval;
}



static char gpib_write__doc__[] =
""
;

static PyObject* gpib_write(PyObject *self, PyObject *args)
{
        char *command;
        int  device;

	if (!PyArg_ParseTuple(args, "is",&device,&command))
		return NULL;
	if( ibwrt(device,command,strlen(command)) & ERR ){
	  PyErr_SetString(GpibError,"Write Error: ibwrt");
	  return NULL;
	}

	Py_INCREF(Py_None);
	return Py_None;
}

static char gpib_writebin__doc__[] =
""
;

static PyObject* gpib_writebin(PyObject *self, PyObject *args)
{
        char *command;
        int device;
        int length;
	int cmdlength;

        if (!PyArg_ParseTuple(args, "is#i",&device,&command,&cmdlength,&length))
                return NULL;
        if( ibwrt(device,command,length) & ERR ){
           PyErr_SetString(GpibError,"Write Error: ibwrt");
           return NULL;
        }

        Py_INCREF(Py_None);
        return Py_None;
}


static char gpib_writea__doc__[] =
""
;

static PyObject* gpib_writea(PyObject *self, PyObject *args)
{
        char *command;
        int  device;

	if (!PyArg_ParseTuple(args, "is",&device, &command))
		return NULL;
	if( ibwrta(device, command, strlen(command)) & ERR ){
	  PyErr_SetString(GpibError,"Async Write Error: ibwrta");
	  return NULL;
	}

	return Py_BuildValue("i", ibsta);
}


static char gpib_cmd__doc__[] =
""
;

static PyObject* gpib_cmd(PyObject *self, PyObject *args)
{
        char *command;
        int  device;

	if (!PyArg_ParseTuple(args, "is",&device,&command))
		return NULL;
	if( ibcmd(device, command, strlen(command)) & ERR ){
	  PyErr_SetString(GpibError,"Command Error: cmd");
	  return NULL;
	}

	return Py_BuildValue("i", ibsta);
}

static char gpib_ren__doc__[] =
""
;

static PyObject* gpib_ren(PyObject *self, PyObject *args)
{
        int device;
        int val;

	if (!PyArg_ParseTuple(args, "ii",&device,&val))
		return NULL;

	if( ibsre(device,val) & ERR){
	  PyErr_SetString(GpibError,"Ren Error: ibsre() failed");
	  return NULL;
	}

	return Py_BuildValue("i", ibsta);
}


static char gpib_clear__doc__[] =
""
;

static PyObject* gpib_clear(PyObject *self, PyObject *args)
{
        int device;

	if (!PyArg_ParseTuple(args, "i",&device))
		return NULL;

	if( ibclr(device) & ERR){
	  PyErr_SetString(GpibError,"Clear Error: ibclr() failed");
	  return NULL;
	}


	Py_INCREF(Py_None);
	return Py_None;
}


static char gpib_ifc__doc__[] =
""
;

static PyObject* gpib_ifc(PyObject *self, PyObject *args)
{
        int device;

	if (!PyArg_ParseTuple(args, "i",&device))
		return NULL;

	SendIFC(device);

	Py_INCREF(Py_None);
	return Py_None;
}


static char gpib_close__doc__[] =
""
;

static PyObject* gpib_close(PyObject *self, PyObject *args)
{
    int device;
	char lockname[LOCKNAME_SIZE];

	if (!PyArg_ParseTuple(args, "i",&device))
		return NULL;

	get_lockname(lockname, LOCKNAME_SIZE, device);
    dev_unlock(lockname, getpid());

	if( ibonl(device, 0) & ERR ){
	  PyErr_SetString(GpibError,"Close Error: ibonl() failed");
	  return NULL;
	}

	Py_INCREF(Py_None);
	return Py_None;
}

static char gpib_wait__doc__[] =
""
;

static PyObject* gpib_wait(PyObject *self, PyObject *args)

{
        int device;
        int mask;

	if (!PyArg_ParseTuple(args, "ii",&device, &mask))
		return NULL;

	if(ibwait(device, mask) & ERR) {
	  PyErr_SetString(GpibError,"Wait Error: ibwait() failed");
	  return NULL;
	}

	return Py_BuildValue("i", ibsta);
}

static char gpib_tmo__doc__[] =
""
;

static PyObject* gpib_tmo(PyObject *self, PyObject *args)

{
        int device;
        int value;

	if (!PyArg_ParseTuple(args, "ii",&device,&value))
		return NULL;
	if( ibtmo(device, value) & ERR){
	  PyErr_SetString(GpibError,"Timeout Error: ibtmo() failed");
	  return NULL;
	}
	Py_INCREF(Py_None);
	return Py_None;
}

static char gpib_rsp__doc__[] =
""
;

static PyObject* gpib_rsp(PyObject *self, PyObject *args)
{
        int device;
	char spr;

	if (!PyArg_ParseTuple(args, "i",&device))
		return NULL;

	if( ibrsp(device, &spr) & ERR){
	  PyErr_SetString(GpibError, "Rsp Error: ibrsp() failed");
	  return NULL;
	}
	
	return Py_BuildValue("c", spr);
}

static char gpib_trg__doc__[] =
""
;

static PyObject* gpib_trg(PyObject *self, PyObject *args)
{
        int device;

	if (!PyArg_ParseTuple(args, "i",&device))
		return NULL;

	if( ibtrg(device) & ERR){
	  PyErr_SetString(GpibError, "Trg Error: ibtrg() failed");
	  return NULL;
	}

	Py_INCREF(Py_None);
	return Py_None;
}

static char gpib_ibsta__doc__[] =
""
;

static PyObject* gpib_ibsta(PyObject *self, PyObject *args)
{

	if (!PyArg_ParseTuple(args, ""))
		return NULL;

	return Py_BuildValue("i",ibsta);
}

static char gpib_ibcnt__doc__[] =
""
;

static PyObject* gpib_ibcnt(PyObject *self, PyObject *args)
{

	if (!PyArg_ParseTuple(args, ""))
		return NULL;

	return Py_BuildValue("i",ibcnt);
}

/* List of methods defined in the module */

static struct PyMethodDef gpib_methods[] = {
 {"find",	gpib_find,	1,	gpib_find__doc__},
 {"ibdev",	gpib_ibdev,	1,	gpib_ibdev__doc__},
 {"ibask",	gpib_ibask,	1,	gpib_ibask__doc__},
 {"ibconfig",	gpib_ibconfig,	1,	gpib_ibconfig__doc__},
 {"read",	gpib_read,	1,	gpib_read__doc__},
 {"readbin",	gpib_readbin,	1,	gpib_readbin__doc__},
 {"write",	gpib_write,	1,	gpib_write__doc__},
 {"writea",	gpib_writea,	1,	gpib_writea__doc__},
 {"writebin",	gpib_writebin,	1,	gpib_writebin__doc__},
 {"cmd",	gpib_cmd,	1,	gpib_cmd__doc__},
 {"ren",	gpib_ren,	1,	gpib_ren__doc__},
 {"clear",	gpib_clear,	1,	gpib_clear__doc__},
 {"ifc",	gpib_ifc,	1,	gpib_ifc__doc__},
 {"close",	gpib_close,	1,	gpib_close__doc__},
 {"wait",	gpib_wait,	1,	gpib_wait__doc__},
 {"tmo",	gpib_tmo,	1,	gpib_tmo__doc__},
 {"rsp",	gpib_rsp,	1,	gpib_rsp__doc__},
 {"trg",	gpib_trg,	1,	gpib_trg__doc__},
 {"ibsta",	gpib_ibsta,	1,	gpib_ibsta__doc__},
 {"ibcnt",	gpib_ibcnt,	1,	gpib_ibcnt__doc__},

	{NULL,		NULL}		/* sentinel */
};


/* Initialization function for the module (*must* be called init_gpib) */

static char gpib_module_documentation[] = 
""
;

void init_gpib(void)
{
  PyObject *m, *d;

  /* Create the module and add the functions */
  m = Py_InitModule4("_gpib", gpib_methods, gpib_module_documentation,
    (PyObject*)NULL, PYTHON_API_VERSION);

  /* Add some symbolic constants to the module */
  d = PyModule_GetDict(m);

  GpibError = PyErr_NewException("_gpib.GpibError", NULL, NULL);
  PyDict_SetItemString(d, "GpibError", GpibError);


	/* XXX Add constants here */
	
	/* Check for errors */
	if (PyErr_Occurred())
		Py_FatalError("can't initialize module _gpib");
}

