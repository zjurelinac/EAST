"""
    east.exceptions
    ===============
    Definitions of HTTP and other application exceptions, used inside
    framework implementation as well as in client code.

    :copyright: (c) 2016 by Zvonimir Jurelinac
    :license: MIT
"""

from flask import jsonify


class BaseAPIException(Exception):
    """Base exception, can be represented as an HTTP response."""
    status_code = 500

    def __init__(self, description='', name=None, status_code=None, data={}):
        self.description = description
        self.data = data

        if name:
            self._name = name
        if status_code:
            self.status_code = status_code

    def __str__(self):
        return '%s' % self.description

    def make_response(self):
        return jsonify({'error':
                        {'name': self.name,
                         'message': self.description + ('[%s]' % self.data if self.data else ''),
                         'code': self.status_code}}), self.status_code

    @property
    def name(self):
        return self._name if hasattr(self, '_name') else self.__class__.__name__


# General API errors

class APIMethodNotAllowed(BaseAPIException):
    """Equivalent of werkzeug MethodNotAllowed."""
    description = 'Requested route does not support this method.'
    status_code = 405


class APIFeatureNotImplemented(BaseAPIException):
    """Equivalent of builtin NotImplementedError."""
    description = 'This feature of the API is not yet implemented.'
    status_code = 501


class FileSystemError(BaseAPIException):
    """Error performing filesystem operation."""
    status_code = 500


class RemoteOperationError(BaseAPIException):
    """Error communicating with remote API's and servers."""
    status_code = 500


# Request processing exceptions

class BadParameterError(BaseAPIException):
    """Request parameter is invalid."""
    status_code = 400


class MissingParameterError(BaseAPIException):
    """Required parameter is missing from the request."""
    status_code = 400


# Database errors

class DatabaseError(BaseAPIException):
    """Generic database error."""
    status_code = 500


class IntegrityViolationError(DatabaseError):
    """Database integrity violated."""
    status_code = 409


class ValueNotUniqueError(IntegrityViolationError):
    """Database unique constraint violated."""
    status_code = 409


class DoesNotExistError(DatabaseError):
    """Requested object does not exist in the database."""
    status_code = 404


class ImpossibleRelationshipError(BaseAPIException):
    """Cannot create an impossible relationship."""
    status_code = 400


# JWT authorization exceptions

class JWTException(BaseAPIException):
    """Base JWT Exception."""
    status_code = 400


class MalformedTokenError(JWTException):
    """Provided authorization token is malformed."""
    status_code = 400


class AuthenticationError(JWTException):
    """Attempted action requires authorization, which has failed."""
    status_code = 403


class UnknownUserError(JWTException):
    """User ID encoded in access_token does not match any user in the database."""
    status_code = 404
