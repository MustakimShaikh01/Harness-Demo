from decimal import Decimal, InvalidOperation
import re

class ToolValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message); self.code = code; self.message = message

def positive_money(value: object, currency: str = "INR") -> Decimal:
    if currency.upper() != "INR": raise ToolValidationError("INVALID_CURRENCY", "Only INR is supported")
    try: amount = Decimal(str(value))
    except (InvalidOperation, ValueError): raise ToolValidationError("INVALID_AMOUNT", "Amount must be a valid decimal")
    if not amount.is_finite(): raise ToolValidationError("INVALID_AMOUNT", "Amount must be a finite decimal")
    if amount <= 0: raise ToolValidationError("INVALID_AMOUNT", "Amount must be positive")
    if amount.as_tuple().exponent < -2: raise ToolValidationError("INVALID_AMOUNT", "Amount supports at most two decimal places")
    return amount.quantize(Decimal("0.01"))

def account_id(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"acct_[A-Za-z0-9_-]+", value):
        raise ToolValidationError("INVALID_ACCOUNT", "Invalid account identifier")
    return value
