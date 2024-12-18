from src.variables import NETWORK_NAME

BEACONCHAIN_URL_TEMPLATE = "[{0}](https://{1}.beaconcha.in/slot/{0})"


def beaconchain(slot) -> str:
    return BEACONCHAIN_URL_TEMPLATE.format(slot, NETWORK_NAME)
