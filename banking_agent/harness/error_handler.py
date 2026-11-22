from .validation import ToolValidationError
from ..storage.json_store import CorruptedJsonError, PersistenceError

def error_contract(exc: Exception) -> dict:
    if isinstance(exc, ToolValidationError):
        return {"success":False,"error":{"category":exc.code,"message":exc.message}}
    if isinstance(exc, PermissionError):
        return {"success":False,"error":{"category":"PERMISSION_DENIED","message":str(exc)}}
    if isinstance(exc, LookupError):
        return {"success":False,"error":{"category":"NOT_FOUND","message":str(exc)}}
    if isinstance(exc, FileNotFoundError):
        return {"success":False,"error":{"category":"DATA_MISSING","message":"Required demo data is missing"}}
    if isinstance(exc, CorruptedJsonError):
        return {"success":False,"error":{"category":"CORRUPTED_JSON","message":"Stored demo data is malformed"}}
    if isinstance(exc, PersistenceError):
        return {"success":False,"error":{"category":"DATA_ERROR","message":"Required demo data could not be read or written safely"}}
    return {"success":False,"error":{"category":"INTERNAL_ERROR","message":"The operation could not be completed safely"}}
