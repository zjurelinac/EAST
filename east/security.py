"""
    east.security
    =============
    Custom JWT (JSON Web Tokens) Flask extension for API user authentication,
    various security helpers

    :copyright: (c) 2016 by Zvonimir Jurelinac
    :license: MIT
"""

from datetime import datetime, timedelta
from functools import wraps

import jwt

from flask import _request_ctx_stack, current_app, request
from werkzeug.local import LocalProxy
from werkzeug.security import generate_password_hash

from .exceptions import *


_jwt = LocalProxy(lambda: current_app.extensions['jwt'])


class JWT:
    """
    Flask JWT security extension

    Enables API access authentication using JSON Web Tokens. Design inspired by
    Flask-JWT. Requires PyJWT.
    """

    CONFIG_DEFAULTS = {
        'JWT_ALGORITHM': 'HS256',
        'JWT_LEEWAY': timedelta(seconds=10),
        'JWT_AUTH_HEADER_PREFIX': 'Bearer',
        'JWT_EXPIRATION_DELTA': timedelta(seconds=300),
        'JWT_NOT_BEFORE_DELTA': timedelta(seconds=0)
    }

    def __init__(self, app, get_identity_handler=None):
        for k, v in JWT.CONFIG_DEFAULTS.items():
            app.config.setdefault(k, v)
        app.config.setdefault('JWT_SECRET_KEY', app.config['SECRET_KEY'])

        if not hasattr(app, 'extensions'):
            app.extensions = {}

        self.get_identity = get_identity_handler

        app.extensions['jwt'] = self


def jwt_required(f):
    """
    JWT protection decorator

    Expects to find `Authorization` header field of the following format:
        `Authorization: JWT token_value`
    Where `token_value` is a valid JWT token.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        header = request.headers.get('Authorization', None)

        if header is None:
            raise AuthenticationError('Authorization token not provided.')

        header_parts = header.split()

        if (len(header_parts) != 2 or header_parts[0] != current_app.config['JWT_AUTH_HEADER_PREFIX']):
            raise MalformedTokenError('Provided authorization token header is malformed: `{}`.'.format(header))

        token = header_parts[1]
        options = {claim: True for claim in ['verify_signature', 'verify_exp',
                                             'verify_nbf', 'verify_iat', 'require_exp',
                                             'require_nbf', 'require_iat']}
        try:
            payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'],
                                 options=options, algorithms=[current_app.config['JWT_ALGORITHM']],
                                 leeway=current_app.config['JWT_LEEWAY'])
        except Exception as e:
            raise MalformedTokenError(str(e))

        _request_ctx_stack.top.user = user = _jwt.get_identity(payload)

        if user is None:
            raise UnknownUserError('There is no user with a given `user_id` in the database.')

        return f(*args, **kwargs)
    return decorated_function


def generate_access_token(user_id, **extras):
    """Generate JWT access token for given user_id"""
    iat = datetime.utcnow()
    exp = iat + current_app.config.get('JWT_EXPIRATION_DELTA')
    nbf = iat + current_app.config.get('JWT_NOT_BEFORE_DELTA')

    access_token = jwt.encode({'exp': exp, 'iat': iat, 'nbf': nbf, 'user_id': user_id},
                              current_app.config['JWT_SECRET_KEY'],
                              algorithm=current_app.config['JWT_ALGORITHM'])
    data = {'access_token': access_token.decode('utf-8'), 'user_id': user_id}
    data.update(extras)
    return data


def active_user():
    """Return user that made the current request"""
    return getattr(_request_ctx_stack.top, 'user', None)


def make_password_hash(password):
    """Make a (relatively) secure salted password hash of a given password"""
    return generate_password_hash(password, method='pbkdf2:sha512:100000', salt_length=16)
