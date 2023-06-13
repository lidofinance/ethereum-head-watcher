import logging
from abc import ABC
from http import HTTPStatus
from typing import Optional, Tuple, Sequence, Callable
from urllib.parse import urljoin, urlparse

from prometheus_client import Histogram
from requests import Session, Response
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from src.typings import InfinityType

logger = logging.getLogger(__name__)


class NoHostsProvided(Exception):
    pass


class ForceUseFallback(Exception):
    pass


class NotOkResponse(Exception):
    status: int
    text: str

    def __init__(self, *args, status: int, text: str):
        self.status = status
        self.text = text
        super().__init__(*args)


class HTTPProvider(ABC):
    """
    Base HTTP Provider with metrics and retry strategy integrated inside.
    """

    PROMETHEUS_HISTOGRAM: Histogram
    HTTP_REQUEST_TIMEOUT: float
    HTTP_REQUEST_RETRY_COUNT: int
    HTTP_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS: float
    HTTP_REQUEST_RETRY_STATUS_FORCELIST = [418, 429, 500, 502, 503, 504]

    def __init__(self, hosts: list[str]):
        if not hosts:
            raise NoHostsProvided(f"No hosts provided for {self.__class__.__name__}")

        self.hosts = hosts

        self.default_retry_strategy = Retry(
            total=self.HTTP_REQUEST_RETRY_COUNT,
            status_forcelist=self.HTTP_REQUEST_RETRY_STATUS_FORCELIST,
            backoff_factor=self.HTTP_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS,
        )

    @staticmethod
    def _urljoin(host, url):
        if not host.endswith('/'):
            host += '/'
        return urljoin(host, url)

    def _prepare_session(self, custom_retry_strategy: Retry | None) -> Session:
        adapter = HTTPAdapter(max_retries=custom_retry_strategy or self.default_retry_strategy)
        session = Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def get(
        self,
        endpoint: str,
        path_params: Optional[Sequence[str | int]] = None,
        query_params: Optional[dict] = None,
        force_raise: Callable[..., Exception | None] = lambda _: None,
        force_use_fallback: Callable[..., bool] = lambda _: False,
        timeout: Optional[float | InfinityType] = None,
        retry_strategy: Retry | None = None,
    ) -> tuple[dict | list, dict]:
        """
        Get request with fallbacks
        Returns (data, meta) or raises exception

        force_raise - function that returns an Exception if it should be thrown immediately.
        Sometimes NotOk response from first provider is the response that we are expecting.
        """
        errors: list[Exception] = []

        for host in self.hosts:
            try:
                result: tuple[dict | list, dict] = self._get_without_fallbacks(
                    host, endpoint, path_params, query_params, timeout, retry_strategy
                )
                if force_use_fallback(result):
                    raise ForceUseFallback(
                        'Forced to use fallback. '
                        f'endpoint: [{endpoint}], '
                        f'path_params: [{path_params}], '
                        f'params: [{query_params}]'
                    )
                return result
            except Exception as e:  # pylint: disable=W0703
                errors.append(e)

                # Check if exception should be raised immediately
                if to_force_raise := force_raise(errors):
                    raise to_force_raise from e

                logger.warning(
                    {
                        'msg': f'[{self.__class__.__name__}] Host [{urlparse(host).netloc}] responded with error',
                        'error': str(e),
                        'provider': urlparse(host).netloc,
                    }
                )

        # Raise error from last provider.
        raise errors[-1]

    def get_stream(
        self,
        endpoint: str,
        path_params: Optional[Sequence[str | int]] = None,
        query_params: Optional[dict] = None,
        force_raise: Callable[..., Exception | None] = lambda _: None,
        timeout: Optional[float | InfinityType] = None,
        retry_strategy: Retry | None = None,
    ) -> Response:
        """
        Get request with fallbacks
        Returns stream
        """
        errors: list[Exception] = []

        for host in self.hosts:
            try:
                return self._get_stream_without_fallbacks(
                    host, endpoint, path_params, query_params, timeout, retry_strategy
                )
            except Exception as e:  # pylint: disable=W0703
                errors.append(e)

                # Check if exception should be raised immediately
                if to_force_raise := force_raise(errors):
                    raise to_force_raise from e

                logger.warning(
                    {
                        'msg': f'[{self.__class__.__name__}] Host [{urlparse(host).netloc}] responded with error',
                        'error': str(e),
                        'provider': urlparse(host).netloc,
                    }
                )

        # Raise error from last provider.
        raise errors[-1]

    def post(
        self,
        endpoint: str,
        path_params: Optional[Sequence[str | int]] = None,
        query_body: Optional[dict | list[dict]] = None,
        force_raise: Callable[..., Exception | None] = lambda _: None,
        timeout: Optional[float | InfinityType] = None,
        retry_strategy: Retry | None = None,
    ) -> Tuple[dict | list, dict]:
        """
        Post request with fallbacks
        Returns (data, meta) or raises exception

        force_raise - function that returns an Exception if it should be thrown immediately.
        Sometimes NotOk response from first provider is the response that we are expecting.
        """
        errors: list[Exception] = []

        for host in self.hosts:
            try:
                return self._post_without_fallbacks(host, endpoint, path_params, query_body, timeout, retry_strategy)
            except Exception as e:  # pylint: disable=W0703
                errors.append(e)

                # Check if exception should be raised immediately
                if to_force_raise := force_raise(errors):
                    raise to_force_raise from e

                logger.warning(
                    {
                        'msg': f'[{self.__class__.__name__}] Host [{urlparse(host).netloc}] responded with error',
                        'error': str(e),
                        'provider': urlparse(host).netloc,
                    }
                )

        # Raise error from last provider.
        raise errors[-1]

    def _get_stream_without_fallbacks(
        self,
        host: str,
        endpoint: str,
        path_params: Optional[Sequence[str | int]] = None,
        query_params: Optional[dict] = None,
        timeout: Optional[float | InfinityType] = None,
        retry_strategy: Retry | None = None,
    ) -> Response:
        """
        Simple get request without fallbacks
        Returns data stream or raises exception
        """
        complete_endpoint = endpoint.format(*path_params) if path_params else endpoint

        with self.PROMETHEUS_HISTOGRAM.time() as t:
            try:
                response = self._prepare_session(retry_strategy).get(
                    self._urljoin(host, complete_endpoint if path_params else endpoint),
                    params=query_params,
                    stream=True,
                    timeout=None if isinstance(timeout, InfinityType) else timeout or self.HTTP_REQUEST_TIMEOUT,
                )
            except Exception as error:
                logger.debug({'msg': str(error)})
                t.labels(
                    endpoint=endpoint,
                    code=0,
                    domain=urlparse(host).netloc,
                )
                raise error

            t.labels(
                endpoint=endpoint,
                code=response.status_code,
                domain=urlparse(host).netloc,
            )

            if response.status_code != HTTPStatus.OK:
                response_fail_msg = f'Response from {complete_endpoint} [{response.status_code}] with text: "{str(response.text)}" returned.'
                logger.debug({'msg': response_fail_msg})
                raise NotOkResponse(response_fail_msg, status=response.status_code, text=response.text)

        return response

    def _get_without_fallbacks(
        self,
        host: str,
        endpoint: str,
        path_params: Optional[Sequence[str | int]] = None,
        query_params: Optional[dict] = None,
        timeout: Optional[float | InfinityType] = None,
        retry_strategy: Retry | None = None,
    ) -> tuple[dict | list, dict]:
        """
        Simple get request without fallbacks
        Returns (data, meta) or raises exception
        """
        complete_endpoint = endpoint.format(*path_params) if path_params else endpoint

        with self.PROMETHEUS_HISTOGRAM.time() as t:
            try:
                response = self._prepare_session(retry_strategy).get(
                    self._urljoin(host, complete_endpoint if path_params else endpoint),
                    params=query_params,
                    timeout=None if isinstance(timeout, InfinityType) else timeout or self.HTTP_REQUEST_TIMEOUT,
                )
            except Exception as error:
                logger.debug({'msg': str(error)})
                t.labels(
                    endpoint=endpoint,
                    code=0,
                    domain=urlparse(host).netloc,
                )
                raise error

            t.labels(
                endpoint=endpoint,
                code=response.status_code,
                domain=urlparse(host).netloc,
            )

            if response.status_code != HTTPStatus.OK:
                response_fail_msg = f'Response from {complete_endpoint} [{response.status_code}] with text: "{str(response.text)}" returned.'
                logger.debug({'msg': response_fail_msg})
                raise NotOkResponse(response_fail_msg, status=response.status_code, text=response.text)

            try:
                json_response = response.json()
            except Exception as error:
                response_fail_msg = f'Response from {complete_endpoint} [{response.status_code}] with text: "{str(response.text)}" returned.'
                logger.debug({'msg': response_fail_msg})
                raise error

        if 'data' in json_response:
            data = json_response['data']
            meta = json_response
        else:
            data = json_response
            meta = {}

        return data, meta

    def _post_without_fallbacks(
        self,
        host: str,
        endpoint: str,
        path_params: Optional[Sequence[str | int]] = None,
        query_body: Optional[dict | list] = None,
        timeout: Optional[float | InfinityType] = None,
        retry_strategy: Retry | None = None,
    ) -> Tuple[dict | list, dict]:
        """
        Simple post request without fallbacks
        Returns (data, meta) or raises exception
        """
        complete_endpoint = endpoint.format(*path_params) if path_params else endpoint

        with self.PROMETHEUS_HISTOGRAM.time() as t:
            try:
                response = self._prepare_session(retry_strategy).post(
                    self._urljoin(host, complete_endpoint if path_params else endpoint),
                    json=query_body,
                    timeout=None if isinstance(timeout, InfinityType) else timeout or self.HTTP_REQUEST_TIMEOUT,
                )
            except Exception as error:
                logger.debug({'msg': str(error)})
                t.labels(
                    endpoint=endpoint,
                    code=0,
                    domain=urlparse(host).netloc,
                )
                raise error

            t.labels(
                endpoint=endpoint,
                code=response.status_code,
                domain=urlparse(host).netloc,
            )

            if response.status_code != HTTPStatus.OK:
                response_fail_msg = f'Response from {complete_endpoint} [{response.status_code}] with text: "{str(response.text)}" returned.'
                logger.debug({'msg': response_fail_msg})
                raise NotOkResponse(response_fail_msg, status=response.status_code, text=response.text)

            try:
                json_response = response.json()
            except Exception as error:
                response_fail_msg = f'Response from {complete_endpoint} [{response.status_code}] with text: "{str(response.text)}" returned.'
                logger.debug({'msg': response_fail_msg})
                raise error

        if 'data' in json_response:
            data = json_response['data']
            del json_response['data']
            meta = json_response
        else:
            data = json_response
            meta = {}

        return data, meta
