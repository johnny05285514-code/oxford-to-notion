import httpx
import pytest
from notion_client.errors import APIErrorCode, APIResponseError, RequestTimeoutError

from exceptions import NotionConnectionError
from notion_connection import ConnectionResult, check_notion_connection
from notion_writer import REQUIRED_SCHEMA


class Endpoint:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def retrieve(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class FakeClient:
    def __init__(self, database_response=None, data_source_response=None):
        self.databases = Endpoint(
            database_response
            if database_response is not None
            else {"data_sources": [{"id": "data-source-id"}]}
        )
        self.data_sources = Endpoint(
            data_source_response
            if data_source_response is not None
            else {"properties": {name: {"type": kind} for name, kind in REQUIRED_SCHEMA.items()}}
        )


def client_factory(client, received_tokens):
    def factory(*, auth):
        received_tokens.append(auth)
        return client

    return factory


def api_error(status, code):
    response = httpx.Response(
        status,
        request=httpx.Request("GET", "https://api.notion.com/v1/databases/test"),
    )
    return APIResponseError(response, "Notion error", code)


def test_connection_validates_token_database_and_schema():
    client = FakeClient()
    tokens = []

    result = check_notion_connection(
        " test-token ",
        "https://www.notion.so/Vocabulary-11111111222233334444555555555555",
        client_factory=client_factory(client, tokens),
    )

    assert result == ConnectionResult(
        database_id="11111111222233334444555555555555",
        data_source_id="data-source-id",
    )
    assert tokens == ["test-token"]


def test_connection_reports_invalid_token():
    client = FakeClient(database_response=api_error(401, APIErrorCode.Unauthorized))

    with pytest.raises(NotionConnectionError, match="Token 无效"):
        check_notion_connection("bad-token", "database-id", client_factory=client_factory(client, []))


def test_connection_reports_database_not_shared_with_integration():
    client = FakeClient(database_response=api_error(404, APIErrorCode.ObjectNotFound))

    with pytest.raises(NotionConnectionError, match="连接到这个数据库"):
        check_notion_connection("token", "database-id", client_factory=client_factory(client, []))


def test_connection_reports_schema_mismatch():
    schema = {name: {"type": kind} for name, kind in REQUIRED_SCHEMA.items()}
    schema.pop("Examples")
    client = FakeClient(data_source_response={"properties": schema})

    with pytest.raises(NotionConnectionError, match="Examples"):
        check_notion_connection("token", "database-id", client_factory=client_factory(client, []))


def test_connection_reports_timeout():
    client = FakeClient(database_response=RequestTimeoutError())

    with pytest.raises(NotionConnectionError, match="超时"):
        check_notion_connection("token", "database-id", client_factory=client_factory(client, []))


def test_connection_reports_httpx_transport_failure_as_network_error():
    request = httpx.Request("GET", "https://api.notion.com/v1/databases/private")
    client = FakeClient(
        database_response=httpx.ConnectError(
            "private endpoint detail", request=request
        )
    )

    with pytest.raises(NotionConnectionError, match="无法连接 Notion") as error:
        check_notion_connection(
            "token", "database-id", client_factory=client_factory(client, [])
        )

    assert "private endpoint" not in str(error.value)
