from dataclasses import dataclass

from src.utils.dataclass import FromResponse


@dataclass
class LidoKey(FromResponse):
    key: str
    depositSignature: str
    operatorIndex: int
    used: bool
    moduleAddress: str


@dataclass
class LidoNamedKey(LidoKey):
    operatorName: str


@dataclass
class LidoModuleOperators(FromResponse):
    operators: list
    module: dict

# {
#       "operators": [
#         {
#           "index": 0,
#           "active": true,
#           "name": "string",
#           "rewardAddress": "string",
#           "stakingLimit": 0,
#           "stoppedValidators": 0,
#           "totalSigningKeys": 0,
#           "usedSigningKeys": 0
#         }
#       ],
#       "module": {
#         "nonce": 0,
#         "type": "string",
#         "id": 0,
#         "stakingModuleAddress": "string",
#         "moduleFee": {},
#         "treasuryFee": {},
#         "targetShare": {},
#         "status": {},
#         "name": "string",
#         "lastDepositAt": {},
#         "lastDepositBlock": {}
#       }
#     }


@dataclass
class KeysApiStatus(FromResponse):
    appVersion: str
    chainId: int
    elBlockSnapshot: dict
