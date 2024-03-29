import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal, Optional

from unsync import unsync

from src.alerts.common import CommonAlert
from src.handlers.handler import WatcherHandler
from src.metrics.prometheus.duration_meter import duration_meter
from src.providers.consensus.typings import BlockDetailsResponse, FullBlockInfo
from src.variables import ADDITIONAL_ALERTMANAGER_LABELS, NETWORK_NAME

logger = logging.getLogger()


Duty = Literal['proposer', 'attester']
Owner = Literal['user', 'other', 'unknown']


@dataclass
class SlashingInfo:
    index: str
    owner: Owner
    duty: Duty
    operator: Optional[str] = None


class SlashingHandler(WatcherHandler):
    @unsync
    @duration_meter()
    def handle(self, watcher, head: FullBlockInfo):
        slashings = []
        for proposer_slashing in head.message.body.proposer_slashings:
            signed_header_1 = proposer_slashing['signed_header_1']
            proposer_index = signed_header_1['message']['proposer_index']
            proposer_key = watcher.indexed_validators_keys.get(proposer_index)
            if proposer_key is None:
                slashings.append(SlashingInfo(index=proposer_index, owner='unknown', duty='proposer'))
            else:
                if user_key := watcher.user_keys.get(proposer_key):
                    slashings.append(
                        SlashingInfo(
                            index=proposer_index, owner='user', duty='proposer', operator=user_key.operatorName
                        )
                    )
                else:
                    slashings.append(
                        SlashingInfo(
                            index=proposer_index,
                            owner='other',
                            duty='proposer',
                        )
                    )

        for attester_slashing in head.message.body.attester_slashings:
            attestation_1 = attester_slashing['attestation_1']
            attestation_2 = attester_slashing['attestation_2']
            attesters = set(attestation_1['attesting_indices']).intersection(attestation_2['attesting_indices'])
            for attester in attesters:
                attester_key = watcher.indexed_validators_keys.get(attester)
                if attester_key is None:
                    slashings.append(SlashingInfo(index=attester, owner='unknown', duty='attester'))
                else:
                    if user_key := watcher.user_keys.get(attester_key):
                        slashings.append(
                            SlashingInfo(index=attester, owner='user', duty='attester', operator=user_key.operatorName)
                        )
                    else:
                        slashings.append(SlashingInfo(index=attester, owner='other', duty='attester'))

        if not slashings:
            logger.debug({'msg': f'No slashings in block [{head.message.slot}]'})
        else:
            logger.info({'msg': f'Slashings in block [{head.message.slot}]: {len(slashings)}'})
            self._send_alerts(watcher, head, slashings)

        return slashings

    def _send_alerts(self, watcher, head: BlockDetailsResponse, slashings: list[SlashingInfo]):
        user_slashings = [s for s in slashings if s.owner == 'user']
        unknown_slashings = [s for s in slashings if s.owner == 'unknown']
        other_slashings = [s for s in slashings if s.owner == 'other']
        if user_slashings:
            summary = f'🚨🚨🚨 {len(user_slashings)} Our validators were slashed! 🚨🚨🚨'
            description = ''
            by_operator: dict[str, list] = defaultdict(list)
            for slashing in user_slashings:
                by_operator[str(slashing.operator)].append(slashing)
            for operator, operator_slashing in by_operator.items():
                description += f'\n{operator} -'
                by_duty: dict[str, list] = defaultdict(list)
                for slashing in operator_slashing:
                    by_duty[slashing.duty].append(slashing)
                for duty, duty_group in by_duty.items():
                    description += f' Violated duty: {duty} | Validators: '
                    description += (
                        "["
                        + ', '.join(
                            [
                                f'[{slashing.index}](http://{NETWORK_NAME}.beaconcha.in/validator/{slashing.index})'
                                for slashing in duty_group
                            ]
                        )
                        + "]"
                    )
            description += (
                f'\n\nslot: [{head.message.slot}](https://{NETWORK_NAME}.beaconcha.in/slot/{head.message.slot})'
            )
            alert = CommonAlert(name="HeadWatcherUserSlashing", severity="critical")
            self.send_alert(watcher, alert.build_body(summary, description, ADDITIONAL_ALERTMANAGER_LABELS))
        if unknown_slashings:
            summary = f'🚨 {len(unknown_slashings)} unknown validators were slashed!'
            description = ''
            by_duty = {}
            for slashing in unknown_slashings:
                by_duty.setdefault(slashing.duty, []).append(slashing)
            for duty, duty_group in by_duty.items():
                description += f' Violated duty: {duty} | Validators: '
                description += (
                    "["
                    + ', '.join(
                        [
                            f'[{slashing.index}](http://{NETWORK_NAME}.beaconcha.in/validator/{slashing.index})'
                            for slashing in duty_group
                        ]
                    )
                    + "]"
                )
            description += (
                f'\n\nslot: [{head.message.slot}](https://{NETWORK_NAME}.beaconcha.in/slot/{head.message.slot})'
            )
            alert = CommonAlert(name="HeadWatcherUnknownSlashing", severity="critical")
            self.send_alert(watcher, alert.build_body(summary, description))
        if other_slashings:
            summary = f'ℹ️ {len(other_slashings)} other validators were slashed'
            description = ''
            by_duty = {}
            for slashing in other_slashings:
                by_duty.setdefault(slashing.duty, []).append(slashing)
            for duty, duty_group in by_duty.items():
                description += f' Violated duty: {duty} | Validators: '
                description += (
                    "["
                    + ', '.join(
                        [
                            f'[{slashing.index}](http://{NETWORK_NAME}.beaconcha.in/validator/{slashing.index})'
                            for slashing in duty_group
                        ]
                    )
                    + "]"
                )
            description += (
                f'\n\nslot: [{head.message.slot}](https://{NETWORK_NAME}.beaconcha.in/slot/{head.message.slot})'
            )
            alert = CommonAlert(name="HeadWatcherOtherSlashing", severity="info")
            self.send_alert(watcher, alert.build_body(summary, description))
