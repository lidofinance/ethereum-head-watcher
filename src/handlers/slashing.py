import logging
from dataclasses import dataclass
from enum import Enum
from itertools import groupby
from typing import Optional, Literal

from unsync import unsync

from src.alerts.slashing import SlashingAlert
from src.handlers.handler import WatcherHandler
from src.metrics.prometheus.duration_meter import duration_meter
from src.providers.consensus.typings import BlockDetailsResponse

logger = logging.getLogger()


Duty = Literal['proposer', 'attester']
Owner = Literal['lido', 'other', 'unknown']


@dataclass
class SlashingInfo:
    index: str
    owner: Owner
    duty: Duty
    operator: Optional[str] = None


class SlashingHandler(WatcherHandler):
    @unsync
    @duration_meter()
    def handle(self, watcher, head: BlockDetailsResponse):
        slashings = []
        for proposer_slashing in head.message.body['proposer_slashings']:
            signed_header_1 = proposer_slashing['signed_header_1']
            proposer_index = signed_header_1['message']['proposer_index']
            proposer_key = watcher.indexed_validators_keys.get(proposer_index)
            if proposer_key is None:
                slashings.append(SlashingInfo(index=proposer_index, owner='unknown', duty='proposer'))
            else:
                if lido_key := watcher.lido_keys.get(proposer_key):
                    slashings.append(
                        SlashingInfo(
                            index=proposer_index, owner='lido', duty='proposer', operator=lido_key.operatorName
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

        for attester_slashing in head.message.body['attester_slashings']:
            attestation_1 = attester_slashing['attestation_1']
            attestation_2 = attester_slashing['attestation_2']
            attesters = set(attestation_1['attesting_indices']).intersection(attestation_2['attesting_indices'])
            for attester in attesters:
                attester_key = watcher.indexed_validators_keys.get(attester)
                if attester_key is None:
                    slashings.append(SlashingInfo(index=attester, owner='unknown', duty='attester'))
                else:
                    if lido_key := watcher.lido_keys.get(attester_key):
                        slashings.append(
                            SlashingInfo(index=attester, owner='lido', duty='attester', operator=lido_key.operatorName)
                        )
                    else:
                        slashings.append(SlashingInfo(index=attester, owner='other', duty='attester'))

        if not slashings:
            logger.info({'msg': f'No slashings in block [{head.message.slot}]'})
        else:
            logger.info({'msg': f'Slashings in block [{head.message.slot}]: {len(slashings)}'})
            self._send_alerts(watcher, head, slashings)

        return slashings

    def _send_alerts(self, watcher, head: BlockDetailsResponse, slashings: list[SlashingInfo]):
        lido_slashings = [s for s in slashings if s.owner == 'lido']
        unknown_slashings = [s for s in slashings if s.owner == 'unknown']
        other_slashings = [s for s in slashings if s.owner == 'other']
        if lido_slashings:
            summary = f'🚨🚨🚨 Lido {len(list(lido_slashings))} validators slashed! 🚨🚨🚨'
            description = ''
            by_operator = {}
            for slashing in lido_slashings:
                by_operator.setdefault(slashing.operator, []).append(slashing)
            for operator, operator_slashing in by_operator.items():
                description += f'\n{operator} -'
                by_duty = {}
                for slashing in operator_slashing:
                    by_duty.setdefault(slashing.duty, []).append(slashing)
                for duty, duty_group in by_duty.items():
                    description += f' {duty.capitalize()}s: '
                    description += (
                        "["
                        + ', '.join(
                            [
                                f'[{slashing.index}](http://beaconcha.in/validator/{slashing.index})'
                                for slashing in duty_group
                            ]
                        )
                        + "]"
                    )
            description += f'\n\nslot: [{head.message.slot}](https://beaconcha.in/slot/{head.message.slot})'
            alert = SlashingAlert(name="HeadWatcherLidoSlashing", severity="critical")
            watcher.alertmanager.send_alerts([alert.build_body(summary, description)])
        if unknown_slashings:
            summary = f'🚨 Unknown {len(list(unknown_slashings))} validators slashed!'
            description = ''
            by_duty = {}
            for slashing in other_slashings:
                by_duty.setdefault(slashing.duty, []).append(slashing)
            for duty, duty_group in by_duty.items():
                description += f' {duty.capitalize()}s: '
                description += (
                    "["
                    + ', '.join(
                        [
                            f'[{slashing.index}](http://beaconcha.in/validator/{slashing.index})'
                            for slashing in duty_group
                        ]
                    )
                    + "]"
                )
            description += f'\n\nslot: [{head.message.slot}](https://beaconcha.in/slot/{head.message.slot})'
            alert = SlashingAlert(name="HeadWatcherUnknownSlashing", severity="critical")
            watcher.alertmanager.send_alerts([alert.build_body(summary, description)])
        if other_slashings:
            summary = f'ℹ️ Other {len(list(other_slashings))} validators slashed'
            description = ''
            by_duty = {}
            for slashing in other_slashings:
                by_duty.setdefault(slashing.duty, []).append(slashing)
            for duty, duty_group in by_duty.items():
                description += f' {duty.capitalize()}s: '
                description += (
                    "["
                    + ', '.join(
                        [
                            f'[{slashing.index}](http://beaconcha.in/validator/{slashing.index})'
                            for slashing in duty_group
                        ]
                    )
                    + "]"
                )
            description += f'\n\nslot: [{head.message.slot}](https://beaconcha.in/slot/{head.message.slot})'
            alert = SlashingAlert(name="HeadWatcherOtherSlashing", severity="info")
            watcher.alertmanager.send_alerts([alert.build_body(summary, description)])
