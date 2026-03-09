import pytest

from Backend.DomainLayer.Exceptions import DomainError, ValidationError


class TestDomainError:
    def test_is_exception(self):
        err = DomainError("something went wrong")
        assert isinstance(err, Exception)
        assert str(err) == "something went wrong"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(DomainError):
            raise DomainError("test error")

    def test_caught_as_exception(self):
        with pytest.raises(Exception):
            raise DomainError("test")


class TestValidationError:
    def test_is_domain_error(self):
        err = ValidationError("invalid field")
        assert isinstance(err, DomainError)
        assert isinstance(err, Exception)
        assert str(err) == "invalid field"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(ValidationError):
            raise ValidationError("bad input")

    def test_caught_as_domain_error(self):
        with pytest.raises(DomainError):
            raise ValidationError("bad input")

    def test_empty_message(self):
        err = ValidationError("")
        assert str(err) == ""

    def test_different_errors_are_distinct(self):
        err1 = ValidationError("error 1")
        err2 = ValidationError("error 2")
        assert str(err1) != str(err2)
