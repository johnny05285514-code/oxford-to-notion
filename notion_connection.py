from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
from notion_client import Client
from notion_client.errors import (
    APIErrorCode,
    APIResponseError,
    HTTPResponseError,
    RequestTimeoutError,
)

from config import normalize_notion_database_id
from exceptions import NotionConnectionError, NotionSchemaError
from notion_writer import NotionWriter


@dataclass(frozen=True, slots=True)
class ConnectionResult:
    database_id: str
    data_source_id: str


def check_notion_connection(
    notion_token: str,
    database_value: str,
    *,
    client_factory: Callable[..., Any] = Client,
) -> ConnectionResult:
    """Check credentials, database access, and required properties without writing."""
    token = notion_token.strip()
    raw_database = database_value.strip()
    if not token:
        raise NotionConnectionError("请先填写 Notion Integration Token。")
    if not raw_database:
        raise NotionConnectionError("请先填写 Notion 数据库 URL 或 Database ID。")

    database_id = normalize_notion_database_id(raw_database)
    client = client_factory(auth=token)
    writer = NotionWriter(client, database_id)

    try:
        data_source_id = writer.validate_connection()
    except NotionSchemaError as exc:
        raise NotionConnectionError(
            "数据库字段不符合要求。请重新复制模板或修正字段：" + str(exc)
        ) from exc
    except APIResponseError as exc:
        if exc.code == APIErrorCode.Unauthorized:
            message = "Notion Token 无效或已失效，请重新复制 Integration Token。"
        elif exc.code in {APIErrorCode.ObjectNotFound, APIErrorCode.RestrictedResource}:
            message = "找不到这个数据库。请确认已把 Integration 连接到这个数据库。"
        elif exc.code == APIErrorCode.RateLimited:
            message = "Notion 请求过于频繁，请稍等片刻后重试。"
        elif exc.code in {
            APIErrorCode.ValidationError,
            APIErrorCode.InvalidRequest,
            APIErrorCode.InvalidRequestURL,
        }:
            message = "数据库 URL 或 Database ID 无效，请重新复制完整数据库链接。"
        else:
            message = "Notion API 连接失败，请稍后重试。"
        raise NotionConnectionError(message) from exc
    except RequestTimeoutError as exc:
        raise NotionConnectionError("连接 Notion 超时，请检查网络后重试。") from exc
    except (httpx.RequestError, HTTPResponseError, OSError) as exc:
        raise NotionConnectionError("无法连接 Notion，请检查网络后重试。") from exc

    return ConnectionResult(database_id=database_id, data_source_id=data_source_id)
