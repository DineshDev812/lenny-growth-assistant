from uuid import UUID

from itsdangerous import BadSignature, URLSafeSerializer

from app.core.config import get_settings

_SALT = "lenny-client-id"


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().secret_key, salt=_SALT)


def sign_client_id(client_id: UUID) -> str:
    return _serializer().dumps(str(client_id))


def unsign_client_id(value: str) -> UUID:
    raw = _serializer().loads(value)
    return UUID(str(raw))


def try_unsign_client_id(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return unsign_client_id(value)
    except (BadSignature, ValueError, TypeError):
        return None
