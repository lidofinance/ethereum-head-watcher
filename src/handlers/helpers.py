from src.keys_source.base_source import NamedKey
from src.utils.execution_requests import ExecutionRequestsContext
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


def slot_description(ctx: ExecutionRequestsContext) -> str:
    """
    Slot line of an alert description.

    Since Gloas (EIP-7732) a request is published one block earlier than the state that reflects it,
    so both slots are shown: the one to look the request up in and the one it was applied at.
    """
    if ctx.request_slot == ctx.state_slot:
        return f'Slot: {beaconchain(ctx.request_slot)}'
    return f'Slot: {beaconchain(ctx.request_slot)} (applied at {beaconchain(ctx.state_slot)})'
