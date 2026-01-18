class DomainError(Exception):
    """Base class for domain-level errors."""
    pass


class ValidationError(DomainError):
    """Raised when domain invariants are violated."""
    pass