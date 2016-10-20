"""
    east.helpers
    ============
    Various helper functions and data structures

    :copyright: (c) 2016 by Zvonimir Jurelinac
    :license: MIT
"""

import mistune

from collections import OrderedDict
from datetime import date, datetime

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import html


# Data serialization functions

def serialize(obj, *args):
    """Serialize an object for future JSON encoding"""
    value = obj(*args) if callable(obj) else obj
    return value.isoformat() if isinstance(value, (date, datetime)) else value


def to_jsondict(obj, view=''):
    """Convert Python object to JSON-encodable dictionary"""
    return obj.to_jsondict(view) if hasattr(obj, 'to_jsondict') else obj


def to_jsontype(type):
    """Convert Python type names to Javascript/JSON equivalents"""
    typename = type.__name__ if type else None
    renames = {'str': 'string', 'int': 'integer', 'bool': 'bool'}
    if typename in renames:
        typename = renames[typename]
    return typename


# Meta functions

def clear_json_quotes(json_data):
    """Remove quotes surrounding types from JSON response documentation"""
    lines = []
    for line in json_data.splitlines():
        if ':' in line:
            key, value = line.split(':', maxsplit=1)
            value = value.strip()
            lines.append(key + ': ' + value.strip('",') + (',' if value.endswith(',') else ''))
        else:
            lines.append(' ' * (len(line) - len(line.lstrip(' '))) + line.strip('" '))
    return '\n'.join(lines)


def get_class_plural_name(cls):
    """Convert class name to it's plural form"""
    base = cls.__name__.lower()
    for ending in ('s', 'z', 'x', 'ch', 'sh'):
        if base.endswith(ending):
            return base + 'es'
    if base.endswith('y'):
        return base[:-1] + 'ies'
    else:
        return base + 's'


def parse_argdict(extras):
    """Parse arguments dict - replace all functions by their return values"""
    return [(key, value() if callable(value) else value) for key, value in extras.items()]


# Datastructures

# class OrderedDefaultDict(OrderedDict, defaultdict):
#     def __init__(self, default_factory=None, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.default_factory = default_factory


class OrderedDefaultDict(OrderedDict):
    # Source: http://stackoverflow.com/a/6190500/562769
    def __init__(self, default_factory=None, *a, **kw):
        if (default_factory is not None and not callable(default_factory)):
            raise TypeError('first argument must be callable')
        super().__init__(*a, **kw)
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = self.default_factory,
        return type(self), args, None, None, self.items()

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))

    def __repr__(self):
        return 'OrderedDefaultDict(%s, %s)' % (self.default_factory,
                                               super().__repr__())


class EastMarkdownParser:
    """
    Custom markdown parser

    Supports code highlighting via Pygments and Table of Contents generation
    """

    def __init__(self):

        class EastRenderer(mistune.Renderer):

            def __init__(self, create_toc=False):
                self.create_toc = create_toc
                self.toc_list = []
                self.toc_count = -1
                super().__init__()

            def block_code(self, code, lang):
                if not lang:
                    return '\n<pre><code>%s</code></pre>\n' % \
                        mistune.escape(code)
                lexer = get_lexer_by_name(lang, stripall=True)
                formatter = html.HtmlFormatter()
                return highlight(code, lexer, formatter)

            def header(self, text, level, raw=None):
                if self.create_toc and level == 2:
                    self.toc_list.append(text)
                    self.toc_count += 1
                    return '<h%d id="h-%d">%s</h%d>\n' % (level, self.toc_count, text, level)
                else:
                    return '<h%d>%s</h%d>\n' % (level, text, level)

            def reset_toc(self):
                self.toc_list = []
                self.toc_count = -1

            def toc(self):
                return '\n'.join(['<li class="o-nav-section-item"><a href="#h-%d">%s</a></li>'
                                  % (i, h) for i, h in enumerate(self.toc_list)])

        self.renderer = EastRenderer()
        self.parser = mistune.Markdown(renderer=self.renderer)

    def render(self, raw, create_toc=False):
        self.renderer.create_toc = create_toc
        if create_toc:
            self.renderer.reset_toc()
        return self.parser(raw)
