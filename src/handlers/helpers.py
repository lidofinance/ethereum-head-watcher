from src.keys_source.base_source import NamedKey
from src.providers.consensus.typings import BlockBody
from src.variables import NETWORK_NAME

BEACONCHAIN_URL_TEMPLATE = "[{0}](https://{1}.beaconcha.in/slot/{0})"
BEACONCHAIN_VALIDATOR_URL_TEMPLATE = "[{0}](https://{1}.beaconcha.in/validator/{2})"


def beaconchain(slot) -> str:
    return BEACONCHAIN_URL_TEMPLATE.format(slot, NETWORK_NAME)


def validator_link(title: str, pubkey: str) -> str:
    return BEACONCHAIN_VALIDATOR_URL_TEMPLATE.format(title, NETWORK_NAME, pubkey)


def validator_pubkey_link(pubkey: str, keys: dict[str, NamedKey]) -> str:
    operator = keys[pubkey].operatorName if pubkey in keys else ''
    spacer = ' ' if operator else ''
    title = f'{operator}{spacer}{pubkey}'
    return validator_link(title, pubkey)


def execution_requests_are_external(body: BlockBody) -> bool:
    """
    Whether the execution requests of a block have to be read from outside of the block body.

    Since Gloas (EIP-7732) the block commits to a payload bid only, while the payload and the
    execution requests are revealed by the builder in a separate envelope and are applied to the
    beacon state one block later. Handlers can not read them from the block anymore, and an empty
    `execution_requests` must not be mistaken for a block without requests.
    """
    return body.execution_payload is None and body.execution_requests is None
