from dataclasses import dataclass

from src.utils.dataclass import FromResponse


@dataclass
class LidoKey:
    key: str
    operatorIndex: str
    moduleIndex: str


@dataclass
class LidoNamedKey(LidoKey):
    operatorName: str


@dataclass
class LidoModuleOperators(FromResponse):
    operators: list
    module: dict


@dataclass
class LidoModule(FromResponse):
    nonce: int


@dataclass
class KeysApiStatus(FromResponse):
    appVersion: str
    chainId: int
    elBlockSnapshot: dict
