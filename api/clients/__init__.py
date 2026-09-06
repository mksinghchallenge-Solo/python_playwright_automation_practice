"""API clients - one class per functional area. All inherit BaseAPIClient."""

from api.clients.auth_client import ApiKeyProvider, AuthClient, StaticTokenProvider, TokenManager
from api.clients.base_client import ApiClientError, BaseAPIClient
from api.clients.content_client import ContentClient
from api.clients.example_client import ExampleClient
from api.clients.profile_client import ProfileClient
from api.clients.user_client import UserClient

__all__ = [
    "ApiClientError",
    "ApiKeyProvider",
    "AuthClient",
    "BaseAPIClient",
    "ContentClient",
    "ExampleClient",
    "ProfileClient",
    "StaticTokenProvider",
    "TokenManager",
    "UserClient",
]
