#coding=utf-8
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache

import datetime

from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from account.models import Token
from rest_framework import HTTP_HEADER_ENCODING

def get_authorization_header(request):
    """
    Return request's 'Authorization:' header, as a bytestring.

    Hide some test client ickyness where the header can be unicode.
    """
    auth = request.META.get('HTTP_AUTHORIZATION', b'')
    if isinstance(auth, type('')):
        # Work around django test client oddness
        auth = auth.encode(HTTP_HEADER_ENCODING)
    return auth

class ExpiringTokenAuthentication(BaseAuthentication):

    model = Token

    def authenticate(self, request):
        auth = get_authorization_header(request)

        if not auth:
            return None

        try:
            token = auth.decode()
        except UnicodeError:
            msg = _('Invalid token header. Token string should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(token)
    
    def authenticate_credentials(self, key):
        
        token_cache = 'token_' + key
        cache_user = cache.get(token_cache)
        if cache_user:
            return (cache_user, token_cache)                     # firstly check the token in cache  

        try:
            token = self.model.objects.get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed('认证失败')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('用户被禁止')

        utc_now = datetime.datetime.utcnow()

        if token.created < utc_now - datetime.timedelta(hours=24 * 14):
            raise exceptions.AuthenticationFailed('认证信息过期')

        if token:
            token_cache = 'token_' + key
            cache.set(token_cache, token.user, 24 * 7 * 60 * 60)  # add token_xxx to cache

        return (token.user, token)

    def authenticate_header(self, request):
        return 'Token'