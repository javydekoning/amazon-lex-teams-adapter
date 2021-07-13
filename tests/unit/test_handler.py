import json
import pytest
import os

from unittest import mock
from app import lambda_function
from app.lib.lex_teams_adapter import LexTeamsAdapterConfig


@pytest.fixture()
def event():
    """ Generates API GW Event"""

    with open('events/event.json', 'r') as file:
        data = file.read().replace('\n', '')
    return json.loads(data)


@pytest.fixture
def context():
    return None


def test_lex_teams_adapter():
    config1 = LexTeamsAdapterConfig(
        ms_app_id='x', client_secret='x', valid_tenant_ids=['x'])
    config2 = LexTeamsAdapterConfig.from_json(
        '{"ms_app_id":"x", "client_secret":"x", "valid_tenant_ids":[ "x" ]}')
    configa = {
        "ms_app_id": 'x',
        "client_secret": 'x',
        "valid_tenant_ids": ['x']
    }
    config3 = LexTeamsAdapterConfig(**configa)
    assert config1 == config2 == config3


def test_lambda_handler(event, context, mocker):
    mocker.patch(
        # api_call is from slow.py but imported to main.py
        'app.lambda_function.get_secret',
        return_value='{"ms_app_id":"x","client_secret":"x","valid_tenant_ids":"x"}'
    )
    mocker.patch(
        'app.lambda_function.lexClient.post_text',
        return_value=json.loads(
            '{"message": "Hi there, what can I do for you today?"}'
        )
    )
    mocker.patch(
        'app.lambda_function.postResponseToTeams',
        return_value=200
    )

    ret = lambda_function.lambda_handler(event, context)
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    # assert "message" in ret["body"]
    # assert data["message"] == "hello world"
    # assert "location" in data.dict_keys()
