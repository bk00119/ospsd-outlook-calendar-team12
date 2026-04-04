from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.callback_auth_callback_get_response_callback_auth_callback_get import (
    CallbackAuthCallbackGetResponseCallbackAuthCallbackGet,
)
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    code: None | str | Unset = UNSET,
    error: None | str | Unset = UNSET,
    error_description: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_code: None | str | Unset
    if isinstance(code, Unset):
        json_code = UNSET
    else:
        json_code = code
    params["code"] = json_code

    json_error: None | str | Unset
    if isinstance(error, Unset):
        json_error = UNSET
    else:
        json_error = error
    params["error"] = json_error

    json_error_description: None | str | Unset
    if isinstance(error_description, Unset):
        json_error_description = UNSET
    else:
        json_error_description = error_description
    params["error_description"] = json_error_description

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/auth/callback",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *,
    client: AuthenticatedClient | Client,
    response: httpx.Response,
) -> CallbackAuthCallbackGetResponseCallbackAuthCallbackGet | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = CallbackAuthCallbackGetResponseCallbackAuthCallbackGet.from_dict(response.json())

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    return None


def _build_response(
    *,
    client: AuthenticatedClient | Client,
    response: httpx.Response,
) -> Response[CallbackAuthCallbackGetResponseCallbackAuthCallbackGet | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    code: None | str | Unset = UNSET,
    error: None | str | Unset = UNSET,
    error_description: None | str | Unset = UNSET,
) -> Response[CallbackAuthCallbackGetResponseCallbackAuthCallbackGet | HTTPValidationError]:
    """Callback

     Handle the OAuth callback from Microsoft.

    Args:
        code (None | str | Unset):
        error (None | str | Unset):
        error_description (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CallbackAuthCallbackGetResponseCallbackAuthCallbackGet | HTTPValidationError]

    """
    kwargs = _get_kwargs(
        code=code,
        error=error,
        error_description=error_description,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    code: None | str | Unset = UNSET,
    error: None | str | Unset = UNSET,
    error_description: None | str | Unset = UNSET,
) -> CallbackAuthCallbackGetResponseCallbackAuthCallbackGet | HTTPValidationError | None:
    """Callback

     Handle the OAuth callback from Microsoft.

    Args:
        code (None | str | Unset):
        error (None | str | Unset):
        error_description (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CallbackAuthCallbackGetResponseCallbackAuthCallbackGet | HTTPValidationError

    """
    return sync_detailed(
        client=client,
        code=code,
        error=error,
        error_description=error_description,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    code: None | str | Unset = UNSET,
    error: None | str | Unset = UNSET,
    error_description: None | str | Unset = UNSET,
) -> Response[CallbackAuthCallbackGetResponseCallbackAuthCallbackGet | HTTPValidationError]:
    """Callback

     Handle the OAuth callback from Microsoft.

    Args:
        code (None | str | Unset):
        error (None | str | Unset):
        error_description (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CallbackAuthCallbackGetResponseCallbackAuthCallbackGet | HTTPValidationError]

    """
    kwargs = _get_kwargs(
        code=code,
        error=error,
        error_description=error_description,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    code: None | str | Unset = UNSET,
    error: None | str | Unset = UNSET,
    error_description: None | str | Unset = UNSET,
) -> CallbackAuthCallbackGetResponseCallbackAuthCallbackGet | HTTPValidationError | None:
    """Callback

     Handle the OAuth callback from Microsoft.

    Args:
        code (None | str | Unset):
        error (None | str | Unset):
        error_description (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CallbackAuthCallbackGetResponseCallbackAuthCallbackGet | HTTPValidationError

    """
    return (
        await asyncio_detailed(
            client=client,
            code=code,
            error=error,
            error_description=error_description,
        )
    ).parsed
