"""Keep test subprocesses in a kill-on-close Windows job (stdlib only)."""
import ctypes
from ctypes import wintypes

def contain_children():
    class Basic(ctypes.Structure):
        _fields_=[('PerProcessUserTimeLimit',ctypes.c_int64),('PerJobUserTimeLimit',ctypes.c_int64),('LimitFlags',wintypes.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',wintypes.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',wintypes.DWORD),('SchedulingClass',wintypes.DWORD)]
    class Io(ctypes.Structure):
        _fields_=[(name,ctypes.c_uint64) for name in ['ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount']]
    class Extended(ctypes.Structure):
        _fields_=[('BasicLimitInformation',Basic),('IoInfo',Io),('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateJobObjectW.restype=wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    handle=kernel.CreateJobObjectW(None,None)
    info=Extended();info.BasicLimitInformation.LimitFlags=0x2000
    if not kernel.SetInformationJobObject(handle,9,ctypes.byref(info),ctypes.sizeof(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel.AssignProcessToJobObject(handle,kernel.GetCurrentProcess()):
        raise ctypes.WinError(ctypes.get_last_error())
    return handle
