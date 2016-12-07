"""
    east.testing
    ============
    EastTester class definition - provides REST API testing functionalities

    :copyright: (c) 2016 by Zvonimir Jurelinac
    :license: MIT
"""

import json
import logging
import os

from .helpers import get_class_plural_name


class EastTester:
    """"""

    def __init__(self, app, base_url):
        self.app = app
        self.test_app = app.test_client()
        self.base_url = base_url

        self.headers = {}

        logfile = app.config.get('TESTING_LOG', 'test.log')
        logging.basicConfig(filename=logfile, filemode='w', level=logging.INFO,
                            format='[%(levelname)-7s] %(asctime)s - %(module)s/%(funcName)s ::  %(message)s',
                            datefmt='%Y-%m-%d %I:%M:%S')

    def make_request(self, url, method='GET', data={}, headers={}, no_data=False, full_url=False):
        caller = getattr(self.test_app, method.lower())
        request_url = url if full_url else os.path.join(self.base_url, url)
        response = caller(request_url, data=data, headers=dict(self.headers, **headers))
        return (response, json.loads(response.data.decode())) if not no_data else response

    def test_success(self, url, method='GET', data={}, headers={},
                     status_code=200):
        response, rdata = self.make_request(url, method, data, headers)
        logging.info(rdata)
        assert response.status_code == status_code

    def test_error(self, url, method='GET', data={}, headers={}, error=None):
        response, rdata = self.make_request(url, method, data, headers)
        assert response.status_code == error.status_code
        assert rdata['error']['name'] == error.__name__

    def test_data(self, url, method='GET', data={}, headers={},
                  type=str, status_code=200, view=''):
        response, rdata = self.make_request(url, method, data, headers)
        logging.info(rdata)
        assert response.status_code == status_code
        assert 'data' in rdata
        response_format = ({get_class_plural_name(type[0]):
                            [type[0].document_response(view=view)]}
                           if isinstance(type, list) else
                           type.document_response(view=view))
        obj_compare(response_format, rdata['data'])
        return rdata

    def set_jwt_token(self, token):
        self.headers['Authorization'] = 'Bearer %s' % token

    def clear_jwt_token(self):
        del self.headers['Authorization']


def obj_compare(source, dest):
    if isinstance(source, list):
        assert isinstance(dest, list)
        for item in dest:
            obj_compare(source[0], item)
    elif isinstance(source, dict):
        assert isinstance(dest, dict)
        for key in source:
            assert key in dest
            obj_compare(source[key], dest[key])
    else:
        return
