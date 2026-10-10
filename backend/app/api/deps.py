from uuid import UUID

from fastapi import Request


def get_client_id(request: Request) -> UUID:
    return request.state.client_id
