"""Encrypted local originals, review receipts and credentials; never in library ZIPs."""
import ctypes
import json
import os
import uuid

from cryptography.fernet import Fernet
from fastapi import HTTPException

from .discovery_store import LOCK, data_root, identifier


def folder():
    path = data_root() / '.discovery' / 'private'
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def _windows(data, decrypt=False):
    class Blob(ctypes.Structure):
        _fields_ = [('size', ctypes.c_ulong), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    dll = ctypes.WinDLL('crypt32', use_last_error=True)
    function = dll.CryptUnprotectData if decrypt else dll.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(Blob)]
    function.restype = ctypes.c_int
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise OSError('Local encryption failed')
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        free = ctypes.WinDLL('kernel32').LocalFree
        free.argtypes, free.restype = [ctypes.c_void_p], ctypes.c_void_p
        free(output.data)


def _fernet():
    path = folder() / 'encryption.key'
    if not path.exists():
        with path.open('xb') as stream:
            os.chmod(path, 0o600)
            stream.write(Fernet.generate_key())
    return Fernet(path.read_bytes())


def path_for(group, key):
    return folder() / (identifier(group) + '-' + identifier(key) + '.enc')


def save(group, key, value):
    with LOCK:
        data = json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
        encrypted = b'W' + _windows(data) if os.name == 'nt' else b'F' + _fernet().encrypt(data)
        path = path_for(group, key)
        temporary = path.with_name('.tmp-' + uuid.uuid4().hex)
        try:
            temporary.write_bytes(encrypted)
            os.chmod(temporary, 0o600)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def read(group, key):
    path = path_for(group, key)
    if not path.exists():
        return None
    with LOCK:
        try:
            data = path.read_bytes()
            clear = _windows(data[1:], True) if data[:1] == b'W' and os.name == 'nt' else _fernet().decrypt(data[1:])
            return json.loads(clear)
        except Exception:
            raise HTTPException(409, 'Private data cannot be decrypted on this account. Reconnect or import and review the original again.') from None


def delete(group, key):
    with LOCK:
        path_for(group, key).unlink(missing_ok=True)
