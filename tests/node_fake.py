"""
A consensus node that answers the watcher, with the block bodies a test asks for.

Why it exists: `tests/test_watcher.py` replays real mainnet slot ranges against live providers and asserts on the alert
text those blocks produced. That is a valuable check and an unreliable one — it sometimes fails because a provider
stopped answering `eth_getLogs` inside the timeout, and it cannot be made hermetic by recording fixtures either: the
assertions depend on the mainnet validator set (~2.3M entries).

So the two are split. Those tests keep the real data and are marked `integration`. This fake carries the same logic — a
cycle, a slashing of one of our keys, an exit that is not ours — at a scale that fits in a test file and needs no
network.

Only the endpoints a cycle touches are served, and an unserved path answers 404 rather than a plausible default.
"""

import json
import threading
import time
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

GENESIS_TIME = 1_606_824_023  # mainnet, so that slot arithmetic in the watcher is realistic
SECONDS_PER_SLOT = 12


def current_slot() -> int:
    """
    The slot the chain would be at right now.

    Not cosmetic: the watcher forces its fallback provider when the head it is served is more than four slots behind the
    wall clock, so a fake serving a fixed historical slot fails every cycle for a reason that has nothing to do with
    what is being tested.
    """
    return int((time.time() - GENESIS_TIME) / SECONDS_PER_SLOT)


def root_of(slot: int) -> str:
    return '0x' + f'{slot:064x}'


def attester_slashing(indices: list[str]) -> dict:
    """The shape SlashingHandler reads: the intersection of both attestations is who was slashed."""
    return {
        'attestation_1': {'attesting_indices': indices},
        'attestation_2': {'attesting_indices': indices},
    }


def proposer_slashing(index: str) -> dict:
    return {'signed_header_1': {'message': {'proposer_index': index}}}


def voluntary_exit(index: str) -> dict:
    return {'message': {'validator_index': index}, 'signature': '0x' + 'ef' * 48}


class BeaconNodeFake:
    """
    Serves the endpoints a cycle can touch, and counts requests per endpoint.

    `bodies` maps a slot to the parts of a block body a test cares about; anything not given is empty. `validators` maps
    a validator index to its pubkey — the watcher builds `indexed_validators_keys` from it, which is what decides
    whether a slashing is ours.
    """

    def __init__(
        self,
        head_slot: int | None = None,
        validators: dict[str, str] | None = None,
        bodies: dict[int, dict] | None = None,
    ):
        self.head_slot = head_slot if head_slot is not None else current_slot()
        self.validators = validators or {}
        self.bodies = bodies or {}
        self.requests: Counter = Counter()
        self._server = ThreadingHTTPServer(('127.0.0.1', 0), self._handler_class())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self._server.server_address[:2]
        return f'http://{host}:{port}'

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._server.shutdown()
        self._server.server_close()

    def reset_counts(self):
        self.requests.clear()

    def _handler_class(self):
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler's spelling
                payload = fake.respond_to(urlparse(self.path).path)
                if payload is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                body = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        return Handler

    def respond_to(self, path: str):
        # Counted by endpoint shape rather than by full path: what matters for a budget is how many
        # header reads a day, not which slot each one was for.
        if path == '/eth/v1/beacon/genesis':
            self.requests['genesis'] += 1
            return {
                'data': {
                    'genesis_time': str(GENESIS_TIME),
                    'genesis_validators_root': '0x' + '11' * 32,
                    'genesis_fork_version': '0x00000000',
                }
            }
        if path.startswith('/eth/v1/beacon/headers/'):
            self.requests['headers/{slot}'] += 1
            slot = self._slot_from(path.rsplit('/', 1)[1])
            return {'execution_optimistic': False, 'finalized': False, 'data': self._header(slot)}
        if path.startswith('/eth/v2/beacon/blocks/'):
            self.requests['blocks/{root}'] += 1
            slot = self._slot_from(path.rsplit('/', 1)[1])
            return {'version': 'electra', 'execution_optimistic': False, 'data': self._block(slot)}
        if path.startswith('/eth/v1/beacon/states/') and path.endswith('/validators'):
            self.requests['states/{state}/validators'] += 1
            return {'execution_optimistic': False, 'data': [self._validator(i, k) for i, k in self.validators.items()]}
        return None

    def _slot_from(self, identifier: str) -> int:
        """`head`, a slot number, or a root this fake minted from a slot number."""
        if identifier == 'head':
            return self.head_slot
        if identifier.startswith('0x'):
            return int(identifier, 16)
        return int(identifier)

    def _header(self, slot: int) -> dict:
        return {
            'root': root_of(slot),
            'canonical': True,
            'header': {
                'message': {
                    'slot': str(slot),
                    'proposer_index': '1',
                    'parent_root': root_of(slot - 1),
                    'state_root': root_of(slot),
                    'body_root': root_of(slot),
                },
                'signature': '0x' + 'ab' * 48,
            },
        }

    def _block(self, slot: int) -> dict:
        body = self.bodies.get(slot, {})
        return {
            'message': {
                'slot': str(slot),
                'proposer_index': '1',
                'parent_root': root_of(slot - 1),
                'state_root': root_of(slot),
                'body': {
                    'execution_payload': {'block_number': str(slot)},
                    'voluntary_exits': body.get('voluntary_exits', []),
                    'proposer_slashings': body.get('proposer_slashings', []),
                    'attester_slashings': body.get('attester_slashings', []),
                    'execution_requests': {'deposits': [], 'withdrawals': [], 'consolidations': []},
                },
            },
            'signature': '0x' + 'cd' * 48,
        }

    def _validator(self, index: str, pubkey: str) -> dict:
        return {
            'index': str(index),
            'balance': '32000000000',
            'status': 'active_ongoing',
            'validator': {
                'pubkey': pubkey,
                'withdrawal_credentials': '0x' + '00' * 32,
                'effective_balance': '32000000000',
                'slashed': False,
                'activation_eligibility_epoch': '0',
                'activation_epoch': '0',
                'exit_epoch': '18446744073709551615',
                'withdrawable_epoch': '18446744073709551615',
            },
        }
