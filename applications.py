#-*- coding:utf-8 -*-

import wsgiref, StringIO, datetime, os, stat, mimetypes
from wsgiref import util

import responses



def addSlash(environ, start_response):
    ''' スラッシュを追加 '''

    pathinfo = environ.get('PATH_INFO', '')

    if not pathinfo or pathinfo[-1] != '/':

        msg = 'add slash'

        start_response('303 SeeOther', [('Content-type', 'text/plain'),
                                        ('Content-length', str(len(msg))),
                                        ('Location', util.request_uri(environ)+'/')])

        return msg
    


class StaticFile(object):
    ''' 静的なディレクトリ '''

    def __init__(self, path, index=True, handlers={}, index_files=['index.html', 'index.htm']):

        self.localRoot = path
        self.handlers = handlers
        self.indexFiles = index_files
        self.index = index


    def listContents(self, environ, start_response):
        ''' フォルダ一覧を出力する '''

        if not self.index:
            return responses.forbidden(environ, start_response)
            
        
        subpath = environ.get('PATH_INFO', '')

        abs = os.path.join(self.localRoot, '.' + subpath)
    
        fp = StringIO.StringIO()

        items = os.listdir(abs)

        items.sort()

        print >> fp, '''<html>
<head><title>Index of %s</title></head>''' % subpath

        print >> fp, '''<body>
<dl>
<dt>Indef of %(subpath)s</dd>''' % locals()

        if subpath != '/':
            print >> fp, '''<dd><a href="..">Parent Directory</a></dd>'''

        for item in items:

            it = os.path.join(abs, item)
        
            if os.path.isdir(it):
                item += '/'

            print >> fp, '<dd><a href="%(item)s">%(item)s</a></dd>' % locals()

        print >> fp, '''</dl>
</body>
</html>'''

        size = fp.tell()

        start_response('200 OK', [('Content-type', 'text/html'),
                                  ('Content-length', str(size))])

        fp.seek(0)
                
        return fp


    def publishFile(self, environ, start_response):
        ''' ファイルを出力 '''

        pathinfo = environ.get('PATH_INFO', '')

        abs = os.path.join(self.localRoot, '.' + pathinfo)
        
        # mimetype を取得
        mime, encoding = mimetypes.guess_type(abs)

        st = os.stat(abs)
        size = st[stat.ST_SIZE]

        fp = file(abs)

        ret = []
                
        if mime is not None:
            ret.append(('Content-type', mime))

        ret.append(('Content-length', str(size)))
                    
        start_response('200 OK', ret)

        return fp


    def __call__(self, environ, start_response):
        ''' レスポンス '''

        pathinfo = environ.get('PATH_INFO', '')

        abs = os.path.join(self.localRoot, '.' + pathinfo)


        # ない
        if not os.path.exists(abs):

            handler = self.handlers.get(404, responses.notFound)
            
            return handler(environ, start_response)

        
       
        try:
            # ディレクトリ
            if os.path.isdir(abs):

                if abs[-1] != '/':

                    return responses.seeOther(environ, start_response,
                                              util.request_uri(environ)+'/')
                    
                else:

                    items = os.listdir(abs)

                    # index を探してみる
                    for index in self.indexFiles:

                        indexFile = os.path.join(abs, index)

                        # あった
                        if index in items and os.path.isfile(indexFile):

                            now = environ['PATH_INFO']
                            environ['PATH_INFO'] = os.path.join(now, index)
                            
                            return self.publishFile(environ, start_response)

                    
                    # 一覧表示
                    return self.listContents(environ, start_response)
                    
                    
            else:
                # ファイル
                return self.publishFile(environ, start_response)


        except IOError, e:
            
            handler = self.handlers.get(403, responses.forbidden)

            return handler(environ, start_response)
    
        

def test():
    ''' ユニットテスト ? '''

    from wsgiref import simple_server

    application = StaticFile('/usr/share/doc')

    srv = simple_server.make_server('', 8080, application)

    srv.serve_forever()


def printEnv(environ, start_response):

    import StringIO
    from xml.sax import saxutils

    fp = StringIO.StringIO()

    print >> fp, '''
<html><head><title>Test Print</title><head>
<body>
<table border="1">
'''
    for v in ((k, saxutils.escape(str(environ[k]))) for k in sorted(environ)):
        print >> fp, '<tr><td>%s</td><td>%s</td></tr>' % v
    
    print >> fp, '''
</table>
</body>
</html>
'''
    start_response('200 OK', [])

    fp.seek(0)
    
    return fp



if __name__ == '__main__':
    test()



