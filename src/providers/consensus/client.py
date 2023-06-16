from http import HTTPStatus
from typing import Literal, Union, Callable

from requests import Response
from urllib3 import Retry

from src.metrics.logging import logging
from src.metrics.prometheus.basic import CL_REQUESTS_DURATION
from src.providers.consensus.typings import (
    BlockDetailsResponse,
    BlockHeaderResponseData,
    BlockRootResponse,
    BeaconSpecResponse,
    GenesisResponse,
)
from src.providers.http_provider import HTTPProvider, NotOkResponse
from src.typings import SlotNumber, BlockRoot, Infinity
from src.variables import CL_REQUEST_TIMEOUT, CL_REQUEST_RETRY_COUNT, CL_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS

logger = logging.getLogger(__name__)


LiteralState = Literal['head', 'genesis', 'finalized', 'justified']


class ConsensusClient(HTTPProvider):
    """
    API specifications can be found here
    https://ethereum.github.io/beacon-APIs/

    state_id
    State identifier. Can be one of: "head" (canonical head in node's view), "genesis", "finalized", "justified", <slot>, <hex encoded stateRoot with 0x prefix>.
    """

    PROMETHEUS_HISTOGRAM = CL_REQUESTS_DURATION

    HTTP_REQUEST_TIMEOUT: float = CL_REQUEST_TIMEOUT
    HTTP_REQUEST_RETRY_COUNT = CL_REQUEST_RETRY_COUNT
    HTTP_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS = CL_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS

    API_GET_BLOCK_ROOT = 'eth/v1/beacon/blocks/{}/root'
    API_GET_BLOCK_HEADER = 'eth/v1/beacon/headers/{}'
    API_GET_BLOCK_DETAILS = 'eth/v2/beacon/blocks/{}'
    API_GET_VALIDATORS = 'eth/v1/beacon/states/{}/validators'
    API_GET_SPEC = 'eth/v1/config/spec'
    API_GET_GENESIS = 'eth/v1/beacon/genesis'
    API_GET_EVENTS = 'eth/v1/events'

    def get_config_spec(self):
        """Spec: https://ethereum.github.io/beacon-APIs/#/Config/getSpec"""
        data, _ = self.get(self.API_GET_SPEC)
        if not isinstance(data, dict):
            raise ValueError("Expected mapping response from getSpec")
        return BeaconSpecResponse.from_response(**data)

    def get_genesis(self):
        """
        Spec: https://ethereum.github.io/beacon-APIs/#/Beacon/getGenesis
        """
        data, _ = self.get(self.API_GET_GENESIS)
        if not isinstance(data, dict):
            raise ValueError("Expected mapping response from getGenesis")
        return GenesisResponse.from_response(**data)

    def get_block_root(self, state_id: Union[SlotNumber, BlockRoot, LiteralState]) -> BlockRootResponse:
        """
        Spec: https://ethereum.github.io/beacon-APIs/#/Beacon/getBlockRoot

        There is no cache because this method is used to get finalized and head blocks.
        """
        data, _ = self.get(
            self.API_GET_BLOCK_ROOT,
            path_params=(state_id,),
            force_raise=self.__raise_last_missed_slot_error,
        )
        if not isinstance(data, dict):
            raise ValueError("Expected mapping response from getBlockRoot")
        return BlockRootResponse.from_response(**data)

    def get_block_header(
        self,
        state_id: Union[SlotNumber, BlockRoot, LiteralState],
        force_use_fallback_callback: Callable[..., bool] = lambda _: False,
    ) -> BlockHeaderResponseData:
        """Spec: https://ethereum.github.io/beacon-APIs/#/Beacon/getBlockHeader"""
        # Set special timeout and retry params for this method.
        # It is used for `slashings` handler
        data, _ = self.get(
            self.API_GET_BLOCK_HEADER,
            path_params=(state_id,),
            force_raise=self.__raise_last_missed_slot_error,
            force_use_fallback=force_use_fallback_callback,
            timeout=1.5,
            retry_strategy=Retry(
                total=1, backoff_factor=0.5, status_forcelist=self.HTTP_REQUEST_RETRY_STATUS_FORCELIST
            ),
        )
        if not isinstance(data, dict):
            raise ValueError("Expected mapping response from getBlockHeader")
        resp = BlockHeaderResponseData.from_response(**data)
        return resp

    def get_block_details(self, state_id: Union[SlotNumber, BlockRoot, LiteralState]) -> BlockDetailsResponse:
        """Spec: https://ethereum.github.io/beacon-APIs/#/Beacon/getBlockV2"""
        # Set special timeout and retry params for this method.
        # It is used for `head` request
        data, _ = self.get(
            self.API_GET_BLOCK_DETAILS,
            path_params=(state_id,),
            force_raise=self.__raise_last_missed_slot_error,
            timeout=1.5,
            retry_strategy=Retry(
                total=1, backoff_factor=0.5, status_forcelist=self.HTTP_REQUEST_RETRY_STATUS_FORCELIST
            ),
        )
        if not isinstance(data, dict):
            raise ValueError("Expected mapping response from getBlockV2")
        return BlockDetailsResponse.from_response(**data)

    def get_validators_stream(self, slot_number: SlotNumber) -> Response:
        """Spec: https://ethereum.github.io/beacon-APIs/#/Beacon/getStateValidators"""
        stream = self.get_stream(
            self.API_GET_VALIDATORS,
            path_params=(slot_number,),
        )
        return stream

    def get_chain_reorg_stream(self) -> Response:
        """Spec: https://consensys.github.io/teku/#tag/Events/operation/getEvents"""
        stream = self.get_stream(
            self.API_GET_EVENTS,
            query_params={"topics": "chain_reorg"},
            timeout=Infinity,
        )
        return stream

    @staticmethod
    def parse_validators(data: list[dict], current_indexes: dict[str, str]) -> dict[str, str]:
        for validator in data:
            index = ""
            pubkey = ""
            for key, value in validator.items():
                if key == "index":
                    if value in current_indexes:
                        continue
                    index = value
                elif index != "" and key == "validator":
                    for k, v in value.items():
                        if k == "pubkey":
                            pubkey = v
            if index != "" and pubkey != "":
                current_indexes[index] = pubkey
        return current_indexes

    def __raise_last_missed_slot_error(self, errors: list[Exception]) -> Exception | None:
        """
        Prioritize NotOkResponse before other exceptions (ConnectionError, TimeoutError).
        If status is 404 slot is missed and this should be handled correctly.
        """
        if len(errors) == len(self.hosts):
            for error in errors:
                if isinstance(error, NotOkResponse) and error.status == HTTPStatus.NOT_FOUND:
                    return error

        return None
