from src.keys_source.base_source import NamedKey
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
