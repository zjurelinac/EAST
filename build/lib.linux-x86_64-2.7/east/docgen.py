"""
    east.docgen
    ===========
    East API documentation generation

    Docs format in short:
    (all description fields support Markdown styling)
        - API docs  - name
                    - description
        - Blueprint docs    - name
                            - description
                            - base_url
        - Route docs    - name
                        - url_route
                        - parameters
                        - description
                        - return
                        - exceptions

    :copyright: (c) 2016 by Zvonimir Jurelinac
    :license: MIT
"""

import inspect
import os
import shutil

from collections import defaultdict
from jinja2 import Environment, FileSystemLoader

from .helpers import EastMarkdownParser, OrderedDefaultDict, to_jsontype


class Docs:
    """East API documentation generator"""

    def __init__(self, config):
        self.config = config

        self.api_doc = {}
        self.param_docs = defaultdict(lambda: defaultdict(lambda: ''))
        self.regions = OrderedDefaultDict(lambda: {'doc': None, 'routes': []})
        self.exceptions = {}

    def document_route(self, region, route_doc):
        self.regions[region]['routes'].append(route_doc)

    def document_parameter(self, name, param_doc):
        self.param_docs[name] = param_doc

    def document_region(self, region, region_doc):
        self.regions[region]['doc'] = region_doc

    def document_api(self, api_doc):
        self.api_doc = api_doc

    def generate(self):
        """Generate API documentation and output it to an .html file"""
        docs = {
            'api': self.api_doc,
            'regions': [dict(doc['doc'], routes=[self.make_route_doc(route)
                                                 for route in doc['routes']])
                        for region, doc in self.regions.items()],
        }

        src_assets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       'assets')
        dest_assets_path = os.path.join('app/static', 'assets')
        shutil.rmtree(dest_assets_path, ignore_errors=True)

        env = Environment(loader=FileSystemLoader(src_assets_path))
        parser = EastMarkdownParser()
        env.filters['md'] = parser.render
        template = env.get_template('docs_template.html')
        with open(self.config['EAST_API_DOCS_LOCATION'], 'w+') as f:
            f.write(template.render(docs=docs, renderer=parser.renderer))

        shutil.copytree(os.path.join(src_assets_path, 'styles'), dest_assets_path)

    def make_route_doc(self, route):
        _docstring = inspect.getdoc(route['endpoint'])
        if _docstring:
            _docsections = _docstring.split('\n@')
            name, *description = _docsections[0].splitlines()
            sections = defaultdict(str, (section.split(':', maxsplit=1)
                                         for section in _docsections[1:]))
        else:
            name, description, sections = 'Unknown', '', defaultdict(str)

        parameters = [{
            'name': param['name'],
            'type': (to_jsontype(param['type'] if param['type'] else
                                 self.param_docs[param['name']]['type'])),
            'required': param['default'] is inspect._empty,
            'default': (param['default']
                        if param['default'] is not inspect._empty else None),
            'description': self.param_docs[param['name']]['description'],
            'example': self.param_docs[param['name']]['example'] or None
        } for param in route['params']]

        return {
            'id': route['endpoint'].__name__,
            'name': name,
            'description': '\n'.join(description[1:]),
            'url_rule': route['url_rule'],
            'parameters': parameters,
            'method': route['method'],
            'auth': route['auth'] or '',
            'response': self.make_response_doc(route['return'],
                                               format=sections['response_format'],
                                               status=sections['response_status'],
                                               description=sections['response_description']),
            'errors': ([self.make_error_doc(exc.strip())
                        for exc in sections['exceptions'].split(',')]
                       if sections['exceptions'] else []),
            'examples': sections['examples']
        }

    def make_response_doc(self, response, **kwargs):
        doc = response.document()
        doc.update({k: v for k, v in kwargs.items() if v})
        return doc

    def make_error_doc(self, name):
        exception = self.exceptions[name]
        return {
            'name': exception().name,
            'code': exception.status_code,
            'description': (exception.description
                            if hasattr(exception, 'description')
                            else exception.__doc__)
        }
