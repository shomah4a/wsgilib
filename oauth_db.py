#-*- coding:utf-8 -*-

import elixir as el
import sqlalchemy as al
from sqlalchemy import orm
import contextlib

import oauth


class OAuthDBMixin(object):

    DBPATH = 'sqlite:////oauth.db'
    SESSION_OPTION = dict(autoflush=True)

    
    def __init__(self, *argl, **argd):

        self.engine = el.create_engine(self.DBPATH, echo=True)

        self.Session = orm.scoped_session(orm.sessionmaker(bind=engine,
                                                           **self.SESSION_OPTION))

        self.metadata = el.metadata
        self.metadata.bind = engine


        class RequestToken(el.Entiry):
            '''
            Request Token
            '''

            el.using_options(tablename='requestTokens', session=self.Session)

            token = el.Field(el.Unicode, required=True, index=True)
            secret = el.Field(el.Unicode, required=True)


        class AccessToken(el.Entiry):
            '''
            Access Token
            '''
            el.using_options(tablename='accessTokens', session=self.Session)

            token = el.Field(el.Unicode, required=True, index=True)
            secret = el.Field(el.Unicode, required=True)


        class SessionInfo(el.Entity):
            '''
            Session
            '''
            el.using_options(tablename='sessions', session=self.Session)

            id = el.Field(el.Unicode, required=True, index=True)

            token = el.OneToOne(AccessToken)


        self.RequestToken = RequestToken
        self.AccessToken = AccessToken
        self.SessionInfo = SessionInfo

        el.setup_all()
        el.create_all()

        self.DBSession = lambda: contextlib.closing(self.Session())


    def saveSessionKey(self, session, token, environ):

        with self.DBSession() as sess:

            tok = sess.query(self.AccessToken).filter_by(token=token.token).one()

            s = self.SessionInfo(id=session, token=tok)

            sess.add(s)


    def loadSessionInfo(self, session, environ):

        with self.DBSession() as sess:

            tok = sess.query(self.SessionInfo).filter_by(id=session).one()

            return oauth.AccessToken(tok.token.token, tok,token.secret)            


    def saveRequestToken(self, token, environ):

        with self.DBSession() as sess:

            tok = self.RequestToken(token=token.token,
                                    secret=token.secret)

            sess.add(tok)

        
    def saveAccessToken(self, access_token, environ):
        
        with self.DBSession() as sess:

            tok = self.AccessToken(token=access_token.token,
                                   secret=access_token.secret)

            sess.add(tok)
        


    def getRequestTokenSecret(self, key, environ):

        with self.DBSession() as sess:

            q = sess.query(self.RequestToken).filter_by(token=key)

            if q.count() == 0:
                return None

            result = q.one()
        
        return oauth.RequestToken(result.token, result.secret)


