#-*- coding:utf-8 -*-

import functools
import cgi
import responses
import time
import random
random.seed()

import urllib
import urllib2

import abc
import pprint
import hmac
import hashlib
import Cookie

try:
    import cPickle as pickle
except:
    import pickle


def makeSignature(method, url, secret, token='', params={}):
    '''
    OAuth Signature を作る
    '''
    
    # pprint.pprint(params)

    params = '&'.join(['%s=%s' % (x, params[x]) for x in sorted(params)])

    # print params
    
    method = urllib.quote(method, '')
    url = urllib.quote(url, '')
    params = urllib.quote(params, '')

    param = '&'.join([method, url, params])

    # print 'basestring', param

    key = secret+'&'+token

    signature = hmac.new(
        key,
        param,
        hashlib.sha1).digest().encode('base64').strip()

    # print "key", key
    # print "param", param
    # print "signature", signature
    # print "digest", hmac.new(
    #     key,
    #     param,
    #     hashlib.sha1).digest()

    return signature



class RequestToken(object):

    def __init__(self, token, secret):

        self.token = token
        self.secret = secret



class AccessToken(RequestToken):
    pass


class OAuthClientBase(object):

    __metaclass__ = abc.ABCMeta

    requestTokenURL = abc.abstractproperty()
    authorizeURL = abc.abstractproperty()
    accessTokenURL = abc.abstractproperty()


    def __init__(self, consumer, secret, redirect='/', sessionkey='__SESSION', userinfo='OAUTH_USER'):

        self.consumerKey = consumer
        self.consumerSecret = secret
        self.redirectURL = redirect
        self.sessionKey = sessionkey
        self.userInfo = userinfo


    def makeParams(self, token=None, tokensecret=None, verifier=None):
        '''
        パラメータ作成
        '''

        ts = str(int(time.time()))
        nonce = str(random.getrandbits(64))
        
        params = {
            'oauth_consumer_key': self.consumerKey,
            'oauth_version': '1.0',
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': ts,
            'oauth_nonce': nonce,
        }

        if verifier:
            params['oauth_verifier'] = verifier
        if token:
            params['oauth_token'] = token

        return params
        


    def getRequestToken(self):
        '''
        リクエストトークン取得
        '''

        params = self.makeParams()

        signature = makeSignature('POST',
                                  self.requestTokenURL,
                                  self.consumerSecret,
                                  params=params)

        params['oauth_signature'] = signature

        req = urllib2.Request(self.requestTokenURL,
                              urllib.urlencode(params),
                              )

        fp = urllib2.urlopen(req)

        token = fp.read()

        token = dict(tuple(x.split('=')) for x in token.split('&'))

        return RequestToken(token['oauth_token'], token['oauth_token_secret'])



    def getAccessToken(self, token, verifier, environ):
        '''
        アクセストークン取得
        '''

        params = self.makeParams(token, verifier=verifier)

        reqtoken = self.getRequestTokenSecret(token, environ)

        if reqtoken is None:
            return

        signature = makeSignature('POST',
                                  self.accessTokenURL,
                                  self.consumerSecret,
                                  reqtoken.secret,
                                  params=params)

        params['oauth_signature'] = signature

        req = urllib2.Request(self.accessTokenURL,
                              urllib.urlencode(params),
                              )

        fp = urllib2.urlopen(req)

        token = fp.read()

        token = dict(tuple(x.split('=')) for x in token.split('&'))

        return AccessToken(token['oauth_token'], token['oauth_token_secret'])



    def redirectAuthorizeURL(self, environ, start_response):
        '''
        認証 URL 作成
        '''

        token = self.getRequestToken()

        self.saveRequestToken(token, environ)

        redirectto = self.authorizeURL+'?'+urllib.urlencode(dict(oauth_token=token.token))

        return responses.redirect(redirectto)(environ, start_response)



    def authCallback(self, environ, start_response):
        '''
        認証成功時のコールバック受け取り
        '''

        form = cgi.FieldStorage(environ=environ)

        token = form['oauth_token'].value
        
        verifier = form['oauth_verifier'].value if 'oauth_verifirie' in form else None

        actoken = self.getAccessToken(token, verifier, environ)

        self.saveAccessToken(actoken, environ)

        session = self.makeSessionKey(actoken, environ)

        self.saveSession(session, actoken, environ)

        cookie = environ.get('HTTP_COOKIE')

        ck = Cookie.SimpleCookie(cookie)

        ck[self.sessionKey] = session


        def start_response_wrapper(code, headers, traceback=None):

            cookies = [tuple(y.strip() for y in x.split(':')) for x in ck.output().splitlines()]

            print headers+cookies

            start_response(code, headers+cookies, traceback)
        

        return responses.redirect(self.redirectURL)(environ, start_response_wrapper)



    def oauthSession(self, sessionapp, nosession=None):
        '''
        ユーザ情報をとってくる
        '''

        nosession = (nosession or sessionapp)

        def session(environ, start_response):

            cookie = Cookie.SimpleCookie(environ.get('HTTP_COOKIE'))

            if self.sessionKey not in cookie:
                return nosession(environ, start_response)

            if self.sessionKey in cookie:
                return nosession(environ, start_response)
            
            key = cookie[self.sessionKey].value

            actoken = self.loadSession(key, environ)

            if not actoken:
                return nosession(environ, start_response)

            user = sctoken

            if not user:
                return nosession(environ, start_response)

            environ[self.userInfo] = user

            return sessionapp(environ, start_response)

        return session


    def makeSessionKey(self, token, environ):
        '''
        セッションキーを作る
        '''

        return hashlib.md5(token.token).hexdigest()



    @abc.abstractmethod
    def saveSession(self, session, token, environ):
        '''
        セッションを保存
        '''


    @abc.abstractmethod
    def loadSession(self, key):
        '''
        セッション取得
        '''


    @abc.abstractmethod
    def saveRequestToken(self, token, environ):
        '''
        リクエストトークンを保存
        '''


    @abc.abstractmethod
    def saveAccessToken(self, access_token, environ):
        '''
        アクセストークンを保存
        '''


    @abc.abstractmethod
    def getRequestTokenSecret(self, key, environ):
        '''
        request token から request token secret を取得
        '''



class SessionInfo(object):

    def __init__(self, *args, **argd):

        super(SessionInfo, self).__init__(*args, **argd)

        self.requestTokens = {}
        self.accessTokens = {}
        self.userTokens = {}
        self.sessions = {}


    def saveRequestToken(self, token, environ):

        print 'request token', token.token, token.secret

        self.requestTokens[token.token] = token


    def saveAccessToken(self, token, environ):

        print 'access token', token.token, token.secret

        self.accessTokens[token.token] = token


    def getRequestTokenSecret(self, token, environ):

        return self.requestTokens.get(token)

    
    def saveSession(self, session, token, environ):

        self.sessions[session] = token


    def loadSession(self, key, environ):

        return self.sessions.get(key)



class TwitterBase(OAuthClientBase):

    requestTokenURL = 'https://twitter.com/oauth/request_token'
    authorizeURL = 'https://twitter.com/oauth/authorize'
    accessTokenURL = 'https://twitter.com/oauth/access_token'



if __name__ == '__main__':

    class Twitter(SessionInfo, TwitterBase):
        pass


    tw = Twitter('xxxxxxxxxxxxxxxxxxxxxxxx',
                 'yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy')

    import wsgiref.simple_server

    import middlewares

    app = middlewares.selectApp({'/': tw.redirectAuthorizeURL,
                                 '/callback': tw.authCallback,
                                 })

    wsgiref.simple_server.make_server('', 8080, app).serve_forever()

    
    
