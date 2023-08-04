from web3 import Web3 as _Web3

from src.web3py.extensions import LidoContracts


class Web3(_Web3):
    lido_contracts: LidoContracts
