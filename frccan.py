import ctypes as C
import warnings

_dll = C.CDLL("libFRC_NetworkCommunication.so")

class CANError(RuntimeError):
    pass

def _RETFUNC(name, restype, *params, out=None, library=_dll,
             errcheck=None, handle_missing=False):
    prototype = C.CFUNCTYPE(restype, *tuple(param[1] for param in params))
    paramflags = []
    for param in params:
        if out is not None and param[0] in out:
            dir = 2
        else:
            dir = 1
        if len(param) == 3:
            paramflags.append((dir, param[0], param[2]))
        else:
            paramflags.append((dir, param[0]))
    try:
        func = prototype((name, library), tuple(paramflags))
        if errcheck is not None:
            func.errcheck = errcheck
    except AttributeError:
        if not handle_missing:
            raise
        def func(*args, **kwargs):
            raise NotImplementedError
    return func

def _STATUSFUNC(name, restype, *params, out=None, library=_dll,
                handle_missing=False):
    realparams = list(params)
    realparams.append(("status", C.POINTER(C.c_int32)))
    _inner = _RETFUNC(name, restype, *realparams, out=out, library=library,
                      handle_missing=handle_missing)
    def outer(*args, **kwargs):
        status = C.c_int32(0)
        rv = _inner(*args, status=C.byref(status), **kwargs)
        if status.value != 0:
            if status.value == -44086: raise CANError("invalid buffer")
            if status.value == -44087: raise CANError("message not found")
            if status.value == -44088: raise CANError("not allowed")
            if status.value == -44089: raise CANError("not initialized")
            if status.value == 44087:
                warnings.warn("CAN session mux: no token", RuntimeWarning)
            elif status.value < 0:
                raise CANError("unknown error %d" % status.value)
            else:
                warnings.warn("CAN session mux: unknown warning %d" % status.value,
                              RuntimeWarning)
        return rv
    return outer

CAN_SEND_PERIOD_NO_REPEAT = 0
CAN_SEND_PERIOD_STOP_REPEATING = -1

# Flags in the upper bits of the messageID
CAN_IS_FRAME_REMOTE = 0x80000000
CAN_IS_FRAME_11BIT = 0x40000000

class CANStreamMessage(C.Structure):
    _fields_ = [("messageID", C.c_uint32),
                ("timeStamp", C.c_uint32),
                ("data", C.c_uint8 * 8),
                ("dataSize", C.c_uint8)]

_CANSessionMux_sendMessage = _STATUSFUNC("FRC_NetworkCommunication_CANSessionMux_sendMessage", None, ("messageID", C.c_uint32), ("data", C.POINTER(C.c_uint8)), ("dataSize", C.c_uint8), ("periodMs", C.c_int32))
def CANSessionMux_sendMessage(messageID, data, periodMs):
    size = len(data)
    buffer = (C.c_uint8 * size)(*data)
    _CANSessionMux_sendMessage(messageID, buffer, size, periodMs)

_CANSessionMux_receiveMessage = _STATUSFUNC("FRC_NetworkCommunication_CANSessionMux_receiveMessage", None, ("messageID", C.POINTER(C.c_uint32)), ("messageIDMask", C.c_uint32), ("data", C.POINTER(C.c_uint8)), ("dataSize", C.POINTER(C.c_uint8)), ("timeStamp", C.POINTER(C.c_uint32)), out=["messageID", "dataSize", "timeStamp"])
def CANSessionMux_receiveMessage(messageIDMask):
    buffer = C.c_uint8 * 8
    messageID, dataSize, timeStamp = _CANSessionMux_receiveMessage(messageIDMask, buffer)
    return messageID, [x for x in buffer[0:dataSize]], timeStamp

CANSessionMux_openStreamSession = _STATUSFUNC("FRC_NetworkCommunication_CANSessionMux_openStreamSession", None, ("sessionHandle", C.POINTER(C.c_uint32)), ("messageID", C.c_uint32), ("messageIDMask", C.c_uint32), ("maxMessages", C.c_uint32), out=["sessionHandle"])
CANSessionMux_closeStreamSession = _RETFUNC("FRC_NetworkCommunication_CANSessionMux_closeStreamSession", None, ("sessionHandle", C.c_uint32))

_CANSessionMux_readStreamSession = _STATUSFUNC("FRC_NetworkCommunication_CANSessionMux_readStreamSession", None, ("sessionHandle", C.c_uint32), ("messages", C.POINTER(CANStreamMessage)), ("messagesToRead", C.c_uint32), ("messagesRead", C.POINTER(C.c_uint32)), out=["messagesRead"])
def CANSessionMux_readStreamSession(sessionHandle, messagesToRead):
    messages = CANStreamMessage * messagesToRead
    messagesRead = _CANSessionMux_readStreamSession(sessionHandle, messages, messagesToRead)
    return messages[0:messagesRead]

_CANSessionMux_getCANStatus = _STATUSFUNC("FRC_NetworkCommunication_CANSessionMux_getCANStatus", None, ("percentBusUtilization", C.POINTER(C.c_float)), ("busOffCount", C.POINTER(C.c_uint32)), ("txFullCount", C.POINTER(C.c_uint32)), ("receiveErrorCount", C.POINTER(C.c_uint32)), ("transmitErrorCount", C.POINTER(C.c_uint32)), out=["percentBusUtilization", "busOffCount", "txFullCount", "receiveErrorCount", "transmitErrorCount"])
def CANSessionMux_getCANStatus():
    percentBusUtilization, busOffCount, txFullCount, receiveErrorCount, transmitErrorCount = _CANSessionMux_getCANStatus()
    return dict(percentBusUtilization=percentBusUtilization,
                busOffCount=busOffCount,
                txFullCount=txFullCount,
                receiveErrorCount=receiveErrorCount,
                transmitErrorCount=transmitErrorCount)