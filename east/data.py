"""
    east.data
    =========
    Endpoint return types definitions (ResponseType baseclass, JSON, HTML)

    :copyright: (c) 2016 by Zvonimir Jurelinac
    :license: MIT
"""

import json

from flask import jsonify, render_template
from .helpers import clear_json_quotes, get_class_plural_name, parse_argdict, to_jsondict


class ResponseType:
    """
    East response generator baseclass
    """

    content_type = 'text/plain'
    description = 'Response description'
    status = 200

    @classmethod
    def format(cls, obj):
        """Return a representation of `obj` for an API response"""
        raise NotImplementedError

    @classmethod
    def document(cls):
        """Return a dictionary describing ResponseType's expected return values"""
        return {
            'content_type': cls.content_type,
            'description': cls.description,
            'format': '',
            'status': cls.status
        }


class JSON(ResponseType):
    """
    JSON response generator

    Constructor options include: specifying object type, passing kwargs for conversion,
    appending extra fields to the result
    """

    content_type = 'application/json'
    description = 'JSON-formatted response'
    status = 200

    def __init__(self, *args, view=None, extras={}):
        self.format = self._format
        self.document = self._document

        self.type = args[0] if args else None
        self.view = view
        self.extras = extras

    @classmethod
    def format(cls, obj):
        return jsonify({'data': to_jsondict(obj)})

    def _format(self, obj):
        parsed_obj = None
        if hasattr(self, 'type') and isinstance(self.type, list):
            parsed_obj = {get_class_plural_name(self.type[0]):
                          [to_jsondict(elem, self.view) for elem in obj]}
        else:
            parsed_obj = to_jsondict(obj, self.view)

        if self.extras:
            parsed_obj.update(parse_argdict(self.extras))

        return jsonify({'data': parsed_obj})

    def _document(self):
        format = ''
        base_item = self.type[0] if isinstance(self.type, list) else self.type
        if hasattr(base_item, 'document_response'):
            base_format = base_item.document_response(self.view)
            response_format = {'data':
                               {get_class_plural_name(self.type[0]): [base_format]}
                               if isinstance(self.type, list) else base_format}
            format = clear_json_quotes(json.dumps(response_format, indent=4,
                                                  separators=(', ', ': '),
                                                  sort_keys=True))

        return {
            'content_type': self.content_type,
            'description': self.description,
            'format': '```js\n%s\n```' % format,
            'status': self.status
        }


class HTML(ResponseType):
    """HTML response generator"""

    content_type = 'text/html'
    description = 'HTML response'

    def __init__(self, template, *args, **kwargs):
        self.template = template

    def format(self, obj):
        return render_template(self.template, **obj)
