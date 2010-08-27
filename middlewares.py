#-*- coding:utf-8 -*-

import wsgiref, StringIO, datetime, os, stat, mimetypes
from wsgiref import util

import responses


def nop(application):
    ''' なにもしないミドルウェア (関数版) '''
    
    def f(environ, start_response):
        return application(environ, start_response)

    return f



class Nop(object):
    ''' 何もしないミドルウェア (クラス版) '''
    
    def __init__(self, application):
        self.application = application


    def __call__(self, environ, start_response):
        return self.application(environ, start_response)


    
def addSlash(f):
    ''' スラッシュを追加 '''

    def app(environ, start_response):

        pathinfo = environ.get('PATH_INFO', '')

        if not pathinfo or pathinfo[-1] != '/':

            start_response('303 SeeOther', [('Content-type', 'text/plain'),
                                            ('Content-length', '0'),
                                            ('Location', util.request_uri(environ)+'/')])

            return ''

        return f(environ, start_response)

    
    return app

    
    

def addContentLength(app):
    ''' Content-Length を追加する '''

    def f(environ, start_response):

        def response(status, headers, exc_info=None):

            response.status = status
            response.headers = headers
            response.exc_info = exc_info


        content = app(environ, response)

        # start_response が呼び出されなかった
        if not hasattr(response, 'status'):
            return

        # ヘッダに Content-Length があるかどうか
        for key, value in response.headers:

            # 存在していたらそのまま返す
            if key.lower() == 'content-length':
                start_response(response.status, response.headers, response.exc_info)
                return content

        # Content-Length を計算
        ret = []
        length = 0

        for i in content:
            length += len(i)
            ret.append(i)

        response.headers.append(('Content-Length', str(length)))

        # あとは返すだけ
        start_response(response.status, response.headers, response.exc_info)

        return ret


    return f




def selectApp(table, default=responses.notFound):
    ''' パス分岐 '''

    # パスは長い順にマッチさせる
    table = [(x, table[x]) for x in sorted(table, key=lambda x:len(x), reverse=True)]
    

    def f(environ, start_response):
        ''' リクエストのパスで振り分ける '''

        name = 'SCRIPT_NAME'
        info = 'PATH_INFO'

        scriptname = environ.get(name, '')
        pathinfo = environ.get(info, '')

        for p, app in table:

            if p == '' or p == '/' and pathinfo.startswith(p):
                return app(environ, start_response)

            # 同じパスならそのまま
            # 同じパスで始まっていて、その後にスラッシュがある
            if pathinfo == p or pathinfo.startswith(p) and pathinfo[len(p)] == '/':

                return app(environ, start_response)

        return default(environ, start_response)


    return f

        
            

def selectAppRewrite(table, default=responses.notFound):
    ''' パス分岐 + パス書き換え'''

    # パスは長い順にマッチさせる
    table = [(x, table[x]) for x in sorted(table, key=lambda x:len(x), reverse=True)]
    

    def f(environ, start_response):
        ''' リクエストのパスで振り分ける '''

        name = 'SCRIPT_NAME'
        info = 'PATH_INFO'

        scriptname = environ.get(name, '')
        pathinfo = environ.get(info, '')

        for p, app in table:

            if p == '' or p == '/' and pathinfo.startswith(p):
                return app(environ, start_response)

            # 同じパスならそのまま
            # 同じパスで始まっていて、その後にスラッシュがある
            if pathinfo == p or pathinfo.startswith(p) and pathinfo[len(p)] == '/':

                # パスの書き換えを行う
                scriptname = scriptname + p
                pathinfo = pathinfo[len(p):]

                environ[name] = scriptname
                environ[info] = pathinfo

                return app(environ, start_response)

        return default(environ, start_response)


    return f



def selectMethod(table, default=responses.notImplemented):
    ''' メソッド分岐 '''
    
    def f(environ, start_response):
        ''' リクエストのパスで振り分ける '''

        method = environ.get('REQUEST_METHOD', 'GET')

        return table.get(method, default)(environ, start_response)
        

    return f



class CacheEntry(object):
    ''' キャッシュ一つ分 '''

    def __init__(self, status, headers, content, time):

        self.status = status
        self.headers = headers
        self.content = [x for x in content]
        self.time = time


    def __call__(self, start_response):
        ''' キャッシュデータからレスポンスを生成 '''

        # レスポンスを返す
        start_response(self.status, self.headers)

        return self.content



class SimpleCache(object):
    ''' GET リクエストの結果をキャッシュ '''
    

    def __init__(self, application, interval=3600):

        self.cacheInterval = interval
        self.application = application
        self.cacheTable = {}


    def __call__(self, environ, start_response):
        ''' キャッシュから返す '''

        method = environ['REQUEST_METHOD']
        path = environ.get('PATH_INFO', '')
        

        # キャッシュしない
        if method != 'GET' or environ.get('QUERY_STRING', None):
            return self.application(environ, start_response)

        
        # キャッシュ取得
        cache = self.cacheTable.get(path, None)

        now = datetime.datetime.now()

        # キャッシュが存在していない
        if cache is None:
            return self.makeCache(environ, start_response, path, now)
        

        # キャッシュの生存期間を過ぎた
        if (now - cache.time).seconds > self.cacheInterval:
            return self.makeCache(environ, start_response, path, now)

        
        return cache(start_response)


    def makeCache(self, environ, start_response, path, now):
        ''' アプリケーションを呼び出し、キャッシュする '''

        tmp = []

        # レスポンスを横取りするための関数
        def response(status, headers, exc_info=tmp):

            response.status = status
            response.headers = headers
            response.exc_info = exc_info


        content = self.application(environ, response)

        # 呼び出されなかった
        if not hasattr(response, 'status'):
            return

        # エラーが出たらそのまま返す
        if response.exc_info is not tmp:
            start_response(response.status, response.headers, response.exc_info)
            return content

        # 200 以外
        if response.status.split()[0] != '200':
            start_response(response.status, response.headers)
            return content


        cache = CacheEntry(response.status, response.headers, content, now)

        self.cacheTable[path] = cache

        return cache(start_response)
        


    
