import json
from typing import List, Mapping, Any, Tuple
from dataclasses import dataclass


@dataclass
class LexTeamsAdapterConfig:
    ms_app_id: str
    client_secret: str
    valid_tenant_ids: List[str]

    def __init__(self, ms_app_id: str, client_secret: str, valid_tenant_ids: List[str]):
        self.ms_app_id = ms_app_id
        self.client_secret = client_secret
        self.valid_tenant_ids = valid_tenant_ids

    @classmethod
    def from_json(cls, json_string: str):
        try:
            return cls(**json.loads(json_string))
        except json.JSONDecodeError as err:
            raise err


@dataclass
class LexTeamsAdapter:
    config: LexTeamsAdapterConfig
    first_name: str
    received_msg: str
    tenant_id: str
    type: str

    def __init__(self, config: LexTeamsAdapterConfig, first_name: str, received_msg: str, tenant_id: str, type: str, receivedFrom: dict, conversation: dict):
        self.config = config
        self.first_name = first_name
        self.received_msg = received_msg
        self.tenant_id = tenant_id
        self.type = type
        self.receivedFrom = receivedFrom
        self.conversation = conversation

    @classmethod
    def from_json(cls, config: LexTeamsAdapterConfig, json_string: str):
        object = json.loads(json_string)

        return cls(
            config,
            object["from"]["name"].split(" ")[0],
            object["text"],
            object["conversation"]["tenantId"],
            object["type"],
            object["conversation"],
            object["from"]
        )

    def covert_responseCard(lexResponse):
        # Todo
        return {}


def event():
    """ Generates API GW Event"""

    with open('events/event.json', 'r') as file:
        data = file.read().replace('\n', '')
        body = json.loads(data)["body"]
    return body

config = LexTeamsAdapterConfig.from_json(
    '{"ms_app_id":"x", "client_secret":"x", "valid_tenant_ids":[ "x" ]}')
app = LexTeamsAdapter.from_json(config=config, json_string=event())
print(app)
