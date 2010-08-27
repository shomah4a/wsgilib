#-*- coding:utf-8 -*-

from __future__ import with_statement

from wsgiref import util
import string
import random
random.seed()

try:
    import hashlib
except:
    import md5
    hashlib = md5



class Digest(object):
    ''' Digest 認証なんかをやってみる '''
    
    def __init__(self, application, htdigest, realm, domain='/'):

        self.htdigest = htdigest
        self.realm = realm
        self.application = application
        self.domain = domain


    def __call__(self, environ, start_response):
        ''' ミドルウェア本体 '''
        
        if not self.checkAuth(environ):
            return self.makeAuthHeader(environ, start_response)

        return self.application(environ, start_response)



    def getUserHash(self, uname):
        ''' ユーザのハッシュを取得 '''
        
        with file(self.htdigest) as fp:
            for i in fp:
                
                i = i.strip()

                sp = i.split(':')

                if uname == sp[0] and self.realm == sp[1]:
                    return sp[2]


    def getUri(self, environ):
        ''' uri を生成 '''

        script = environ.get('SCRIPT_NAME', '')
        path = environ.get('PATH_INFO', '')

        uri = '%s%s' % (script, path)

        query = environ.get('QUERY_STRING')

        if query:
            uri += '?%s' % query

        return uri
    

    def checkAuth(self, environ):
        ''' 認証チェック '''

        try:

            auth = environ['HTTP_AUTHORIZATION']
            sp = auth.split(' ', 1)
            authType = sp[0]

            assert authType.lower() == 'digest'
                        
            auth = sp[1]

            params = dict([tuple(x.strip().split('=', 1))
                           for x in auth.split(',')])
            params = dict((x, y.strip('"')) for x, y in params.iteritems())

            assert self.realm == params['realm']

            uname = params['username']

            a1 = self.getUserHash(uname)

            a2 = hashlib.md5('%s:%s' % (environ['REQUEST_METHOD'],
                                    self.getUri(environ))).hexdigest()

            params['a1'] = a1
            params['a2'] = a2

            s = '%(a1)s:%(nonce)s:%(nc)s:%(cnonce)s:%(qop)s:%(a2)s' % params
            
            m = hashlib.md5(s).hexdigest()
            
            if m == params['response']:
                environ['REMOTE_USER'] = uname
                return True

            return False
        
        except:
            import traceback

            traceback.print_exc()
            
            return False


    def makeAuthHeader(self, environ, start_response):

        authType = 'Digest'
        
        chars = string.ascii_letters + string.digits
        salt = ''.join(random.choice(random.choice(chars)) for i in range(11))
        
        values = dict(
            nonce = '"%s"' % hashlib.md5(salt).hexdigest(),
            algorithm = 'MD5',
            qop = '"auth"',
            realm = self.realm,
            domain = '"%s"' % self.domain,
            )

        values = ['%s=%s' % (i, j) for i, j in values.iteritems()]

        auth = '%s %s' % (authType, ', '.join(values))

        ret = 'unauthorized'

        start_response('401 Unauthorized', [('Content-type', 'text/plain'),
                                            ('Content-length', str(len(ret))),
                                            ('WWW-Authenticate', auth),])

        return ret



def test():

    import sys

    htdigest, realm = sys.argv[1:3]

    print 'htdigest', htdigest
    print 'realm', realm

    def authorized(environ, start_response):

        start_response('200 OK', [('Content-type', 'text/plain')])

        return 'authorized'
        
    
    from wsgiref import simple_server

    application = Digest(authorized, htdigest, realm)

    srv = simple_server.make_server('', 8080, application)

    srv.serve_forever()



if __name__ == '__main__':
    test()
