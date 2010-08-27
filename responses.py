#-*- coding:utf-8 -*-

from wsgiref import util


# Redirects


def redirect(location):

    def app(environ, start_response):

        return seeOther(environ, start_response, location)

    return app



def found(environ, start_response, location):
    ''' 恒久的な移動 '''

        
    start_response('301 Moved Permanently', [('Content-type', 'text/plain'),
                                             ('Content-length', str(len(location))),
                                             ('Location', location)])

    return location



def found(environ, start_response, location):
    ''' 一時的な移動 '''

        
    start_response('302 Found', [('Content-type', 'text/plain'),
                                 ('Content-length', str(len(location))),
                                 ('Location', location)])

    return location



def seeOther(environ, start_response, location):
    ''' リダイレクト '''

        
    start_response('303 See Other', [('Content-type', 'text/plain'),
                                    ('Content-length', str(len(location))),
                                    ('Location', location)])

    return location



# Error Responses

def notFound(environ, start_response):

    ret = '%s not found' % util.request_uri(environ)
    
    
    start_response('404 Not Found', [('Content-type', 'text/plain'),
                                    ('Content-length', str(len(ret)))])

    return ret



def notImplemented(environ, start_response):
    ''' 未実装 '''

    ret = '501 Not Implemented'
        
    start_response(ret, [('Content-type', 'text/plain'),
                         ('Content-length', str(len(ret)))])

    return ret



def forbidden(environ, start_response):
    ''' 権限なし '''

    ret = '403 Forbidden'
        
    start_response(ret, [('Content-type', 'text/plain'),
                         ('Content-length', str(len(ret)))])

    return ret
