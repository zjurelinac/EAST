"""
    east.module
    ===========
    East class definition - East object allows defining API routes,
    validating request parameters and generating API documentation

    :copyright: (c) 2016 by Zvonimir Jurelinac
    :license: MIT
"""

import inspect
import os

from functools import wraps
from flask import request, send_from_directory

from .docgen import Docs
from .exceptions import *
from .security import jwt_required


class East:
    """
    East (Easy REST) extension for Flask

    Description
    """

    def __init__(self, flask_app):
        """Create East object for the given `flask_app`"""
        self._flask_app = flask_app
        self._validators = {}
        self._routes = {}
        self._exceptions = {}
        self._docs = (Docs(flask_app.config)
                      if flask_app.config['EAST_GENERATE_API_DOCS'] else None)
        self._base_url = flask_app.config.get('BASE_API_URL', '/')
        self._flask_app.add_url_rule(os.path.join(self._base_url, 'docs'), 'docs', self._serve_docs,
                                     methods=['GET'])

    def register_validator(self, param_name: str, param_validator):
        """Register parameter validator, for all API routes"""
        self._validators[param_name] = param_validator

    def document_api(self, name: str, version: str, description: str, **kwargs):
        """
        Document REST API - provide basic info about it

        :param name:            API name, eg. SocialNet Public API
        :param version:         API version, eg. 2.1.4
        :param description:     API description, overview, general remarks etc.
                                Supports Markdown
        :param **kwargs:        All additional info, such as host, base_url, scheme...
        """
        if self._docs is None:
            raise DocumentationError('Cannot document API, documentation is not generated in this run.')
        self._docs.document_api(dict({'name': name, 'version': version,
                                      'description': description}, **kwargs))

    def document_region(self, region, name: str, base_url: str ='',
                        description: str ='', **kwargs):
        """
        Document API region - provide basic info about it

        :param region:          Flask app or Blueprint object
        :param name:            Region name
        :param base_url:        Region URL prefix
        :param description:     Region description, supports Markdown
        :param **kwargs:        All additional info
        """
        if self._docs is None:
            raise DocumentationError('Cannot document API, documentation is not generated in this run.')
        self._docs.document_region(region, dict({'name': name, 'base_url': base_url,
                                                 'description': description}, **kwargs))

    def document_parameter(self, name: str, type=None, description: str = '',
                           location: str = None, example: str = None, **kwargs):
        """
        Document request parameter, API-wide

        :param name:        Parameter name
        :param type:        Parameter type, as a Python type (ie. str, int),
                            not a string description (ie. 'string', 'float')
        :param description: Parameter description, supports Markdown (inline elements)
        :param location:    Parameter location, ie. 'body', 'url', 'path'
        :param example:     Example parameter value
        :param **kwargs:    All additional info
        """
        if self._docs is None:
            raise DocumentationError('Cannot document API, documentation is not generated in this run.')
        self._docs.document_parameter(name, dict({'type': type, 'description': description,
                                                  'location': location, 'example': example},
                                                 **kwargs))

    def register_exceptions(self, exceptions):
        self._exceptions.update({exception.__name__: exception for exception in exceptions})
        if self._docs:
            self._docs.exceptions = self._exceptions

    def route(self, base, url_rule: str, method: str = 'GET', auth: str = None):
        """
        API route decorator

        :param base:    Flask app or Blueprint object, on which the endpoint
                        should be added
        :param route:   URL route rule (can include path variables) for the given
                        endpoint
        :param method:  HTTP method accepted by the endpoint (default: GET)
        :param auth:    API authentication method, currently only 'JWT' is
                        supported
        """
        def decorator(f):

            if auth == 'JWT':
                f = jwt_required(f)

            params = [{
                'default': param.default,
                'type': param.annotation,
                'name': param.name,
                'auto_fill': True,
                'validator': self._validators.get(param.name, None)
            } if param.annotation is not inspect._empty else {
                'default': inspect._empty,
                'type': None,
                'name': param.name,
                'validator': None,
                'auto_fill': False
            } for param in inspect.signature(f).parameters.values()]

            self._routes[f] = {
                'auth': auth,
                'method': method,
                'endpoint': f,
                'params': params,
                'url_rule': url_rule,
                'return': f.__annotations__['return'] or None
            }

            if self._docs:
                self._docs.document_route(base, self._routes[f])

            @wraps(f)
            def decorated_function(*args, **parsed_params):
                # REWRITE!!!
                for param in self._routes[f]['params']:
                    if param['auto_fill']:
                        raw_value = _get_request_param(param['name'])
                        if raw_value is None and param['default'] is inspect._empty:
                            raise MissingParameterError('Parameter `%s` is not present in the request' % param['name'])
                        try:
                            parsed_value = param['type'](raw_value) if raw_value is not None else param['default']
                            if param['validator'] is not None and raw_value is not None:
                                param['validator'](parsed_value)
                        except Exception as e:
                            raise BadParameterError('Parameter `%s` is invalid [%s]' % (param['name'], e))
                        parsed_params[param['name']] = parsed_value

                output, status = f(*args, **parsed_params), 200
                if isinstance(output, tuple):
                    output, status = output

                return self._routes[f]['return'].format(output), status

            base.add_url_rule(url_rule, f.__name__, decorated_function, methods=[method])

            return decorated_function
        return decorator

    def generate_docs(self):
        """Generate API documentation"""
        self._docs.generate()

    def _serve_docs(self):
        if 'EAST_API_DOCS_LOCATION' not in self._flask_app.config:
            raise DoesNotExistError('API documentation is not available.')
        return send_from_directory("../docs", "docs.html")


def _get_request_param(name: str):
    locations = [request.values, request.files]

    if request.method in ('PATCH', 'POST', 'PUT') and request.is_json:
        locations.append(request.get_json())

    for location in locations:
        if name in location:
            return location[name]


class DocumentationError(RuntimeError):
    pass
