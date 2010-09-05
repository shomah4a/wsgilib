#-*- coding:utf-8 -*-

import elixir as el
import sqlalchemy as al
from sqlalchemy import orm
import contextlib

import oauth


class OAuthDBMixin(object):

    DBPATH = 'sqlite:///oauth.db'
    SESSION_OPTION = dict(autoflush=True)

    
    def __init__(self, *argl, **argd):

        super(OAuthDBMixin, self).__init__(*argl, **argd)

        self.engine = al.create_engine(self.DBPATH, echo=True)

        self.Session = orm.scoped_session(orm.sessionmaker(bind=self.engine,
                                                           **self.SESSION_OPTION))

        self.metadata = el.metadata
        self.metadata.bind = self.engine


        class RequestToken(el.Entity):
            '''
            Request Token
            '''

            el.using_options(tablename='requestTokens', session=self.Session)

            token = el.Field(el.Unicode, required=True, index=True)
            secret = el.Field(el.Unicode, required=True)


        class AccessToken(el.Entity):
            '''
            Access Token
            '''
            el.using_options(tablename='accessTokens', session=self.Session)

            token = el.Field(el.Unicode, required=True, index=True)
            secret = el.Field(el.Unicode, required=True)

            sessions = el.OneToMany('SessionInfo')
            


        class SessionInfo(el.Entity):
            '''
            Session
            '''
            el.using_options(tablename='sessions', session=self.Session)

            sessionId = el.Field(el.Unicode, required=True, index=True)
            createdAt = el.Field(el.DateTime, required=False)

            token = el.ManyToOne(AccessToken, inverse='sessions')

                    
        self.RequestToken = RequestToken
        self.AccessToken = AccessToken
        self.SessionInfo = SessionInfo

        el.setup_all()
        el.create_all()

        self.DBSession = lambda: contextlib.closing(self.Session())


    def saveSession(self, session, token, environ):

        with self.DBSession() as sess:

            tok = sess.query(self.AccessToken).filter_by(token=token.token).one()

            s = self.SessionInfo(sessionId=session, token=tok)

            sess.add(s)
            sess.commit()


    def loadSession(self, session, environ):

        with self.DBSession() as sess:

            tok = sess.query(self.SessionInfo).filter_by(sessionId=session).one()

            return oauth.AccessToken(tok.token.token, tok,token.secret)            


    def saveRequestToken(self, token, environ):

        with self.DBSession() as sess:

            tok = self.RequestToken(token=token.token,
                                    secret=token.secret)

            sess.add(tok)
            sess.commit()

        
    def saveAccessToken(self, access_token, environ):
        
        with self.DBSession() as sess:

            tok = self.AccessToken(token=access_token.token,
                                   secret=access_token.secret)

            sess.add(tok)
            sess.commit()
        


    def getRequestTokenSecret(self, key, environ):

        with self.DBSession() as sess:

            q = sess.query(self.RequestToken).filter_by(token=key)

            if q.count() == 0:
                return None

            result = q.one()
        
        return oauth.RequestToken(result.token, result.secret)



if __name__ == '__main__':

    class Twitter(OAuthDBMixin, oauth.TwitterBase):
        pass


    tw = Twitter('xxxxxxxxxxxxxxxxxxxxxxx',
                 'yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy')

    import wsgiref.simple_server

    import middlewares

    app = middlewares.selectApp({'/': tw.redirectAuthorizeURL,
                                 '/callback': tw.authCallback,
                                 })

    wsgiref.simple_server.make_server('', 8080, app).serve_forever()

