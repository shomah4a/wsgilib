#-*- coding:utf-8 -*-
import cgi
import Cookie
from wsgiref import util

_urlencoded = 'application/x-www-form-urlencoded'
_multipart = 'multipart/form-data'
_plain = 'text/plain'
_accepts = (_urlencoded, _multipart, _plain)



class Request(object):
    ''' リクエストクラス '''

    def __init__(self, environ):
        ''' 初期化 '''

        self.environ = environ
        
        self.param = cgi.FieldStorage(environ['wsgi.input'], environ=environ)

        cookie = environ.get('HTTP_COOKIE', '')
        self.cookie = Cookie.SimpleCookie(cookie)



    def getFirstParam(self, key, default=None):
        ''' パラメータを一つ取得 '''
        return self.param.getfirst(key, default)


    def getListParam(self, key):
        ''' パラメータをリストで取得 '''

        return self.param.getlist(key)


    def getUserName(self):
        ''' ユーザ名 '''

        return self.environ.get('REMOTE_USER')


    def getUri(self, param=True):
        ''' リクエストされた URI を取得 '''

        return util.request_uri(self.environ, param)


    def getScriptName(self):
        ''' スクリプトパス '''
        
        return self.environ.get('SCRIPT_NAME')


    def getPathInfo(self):
        ''' パス情報 '''

        return self.environ.get('PATH_INFO')


    def createResponse(self):
        ''' リクエストからレスポンス生成 '''

        ret = []
        
        # Cookie 設定
        if self.COOKIE:
            for key, value in self.COOKIE:
                ret.append(('Set-Cookie', '%s=%s' % (key, value.value)))

        return ret


def errorhandler(app):

    def f(environ, start_response):

        try:
            return app(environ, start_response)
        except:
            import traceback
            exp = traceback.format_exc()

            start_response('500 InternalServerError', [('content-type', 'text/plain;charset=UTF-8')])

            return exp

    return f
        
    



    
    
