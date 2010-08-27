#-*- coding:utf-8 -*-

import memcache

from wsgiref import util

try:
    import cStringIO as StringIO
except ImportError, e:
    import StringIO


class MemcachedMiddleware(object):
    '''
    memcached でキャッシング
    '''

    def __init__(self, app, hosts,
                 init_argl=(), init_argd={},
                 set_argl=(), set_argd={}):

        self.app = app
        self.hosts = hosts
        self.init_argl = init_argl
        self.init_argd = init_argd

        self.set_argl = set_argl
        self.set_argd = set_argd


    def __call__(self, environ, start_response):
        '''
        キャッシュする
        '''

        # GET 以外はキャッシュしない
        if environ.get('REQUEST_METHOD') != 'GET':
            return self.app(environ, start_response)

        client = memcache.Client(self.hosts,
                                 *self.init_argl,
                                 **self.init_argd)

        uri = util.request_uri(environ)

        bodyKey = uri
        headerKey = 'header_' + uri

        data = client.get_multi([bodyKey, headerKey])
        cbody = data.get(bodyKey)
        cheader = data.get(headerKey)

        if cbody and cheader:
            header = eval(cheader)
            start_response('200 OK', header)
            print 'find cache'
            return cbody


        def start_response_wrap(status, headers, exc_info=None):
            
            start_response_wrap.status = status
            start_response_wrap.headers = headers
            start_response_wrap.exc_info = exc_info


        srw = start_response_wrap
            
        ret = self.app(environ, start_response_wrap)

        if not hasattr(srw, 'status'):
            return

        if srw.exc_info or not srw.status.startswith('200'):
            start_response(srw.status, srw.headers, srw.exc_info)
            return ret


        fp = StringIO.StringIO()

        for line in ret:
            fp.write(line)

        fp.seek(0)


        nocache = client.set_multi({bodyKey:fp.getvalue(),
                                    headerKey:repr(srw.headers)},
                                   *self.set_argl, **self.set_argd)

        start_response(srw.status, srw.headers)

        return fp
        
    
