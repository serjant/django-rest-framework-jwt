# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from datetime import datetime

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from .permissions import IsSuperUser
from .authentication import JSONWebTokenAuthentication
from .serializers import \
    JSONWebTokenSerializer, RefreshAuthTokenSerializer, \
    VerifyAuthTokenSerializer, ImpersonateAuthTokenSerializer
from .settings import api_settings


class BaseJSONWebTokenAPIView(GenericAPIView):
    """Base JWT auth view used for all other JWT views (verify/refresh)."""

    permission_classes = ()
    authentication_classes = ()

    serializer_class = JSONWebTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        user = serializer.validated_data.get('user') or request.user
        token = serializer.validated_data.get('token')
        issued_at = serializer.validated_data.get('issued_at')
        response_data = JSONWebTokenAuthentication. \
            jwt_create_response_payload(token, user, request, issued_at)

        response = Response(response_data)

        if api_settings.JWT_AUTH_COOKIE:
            expiration = (
                datetime.utcnow() + api_settings.JWT_EXPIRATION_DELTA
            )
            response.set_cookie(
                api_settings.JWT_AUTH_COOKIE, token, expires=expiration,
                httponly=True
            )
        return response


class ObtainJSONWebTokenView(BaseJSONWebTokenAPIView):
    """
    API View that receives a POST with a user's username and password.

    Returns a JSON Web Token that can be used for authenticated requests.
    """

    serializer_class = JSONWebTokenSerializer


class VerifyJSONWebTokenView(BaseJSONWebTokenAPIView):
    """
    API View that checks the validity of a token, returning the token if it
    is valid.
    """

    serializer_class = VerifyAuthTokenSerializer


class RefreshJSONWebTokenView(BaseJSONWebTokenAPIView):
    """
    API View that returns a refreshed token (with new expiration) based on
    existing token

    If 'orig_iat' field (original issued-at-time) is found it will first check
    if it's within expiration window, then copy it to the new token.
    """

    serializer_class = RefreshAuthTokenSerializer


class ImpersonateJSONWebTokenView(GenericAPIView):
    """Impersonation View allows superusers to impersonate other
    non-superusers accounts.
    """

    permission_classes = (IsSuperUser, )
    serializer_class = ImpersonateAuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        user = serializer.validated_data.get('user')
        payload = JSONWebTokenAuthentication.jwt_create_payload(user)
        token = JSONWebTokenAuthentication.jwt_encode_payload(payload)
        issued_at = serializer.validated_data.get('issued_at')

        response_data = JSONWebTokenAuthentication. \
            jwt_create_response_payload(token, user, request, issued_at)

        response = Response({"token": response_data["token"], "user": user.pk})

        if api_settings.JWT_IMPERSONATION_COOKIE:
            expiration = (
                datetime.utcnow() + api_settings.JWT_EXPIRATION_DELTA
            )
            response.set_cookie(
                api_settings.JWT_IMPERSONATION_COOKIE, token,
                expires=expiration, httponly=True
            )
        return response


obtain_jwt_token = ObtainJSONWebTokenView.as_view()
verify_jwt_token = VerifyJSONWebTokenView.as_view()
refresh_jwt_token = RefreshJSONWebTokenView.as_view()
impersonate_jwt_token = ImpersonateJSONWebTokenView.as_view()
