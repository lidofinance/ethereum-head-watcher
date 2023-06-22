alerts = [
    {
        'summary': '🚨🚨🚨 2 Lido validators were slashed! 🚨🚨🚨',
        'description': '\nRockLogic GmbH - Violated duty: attester | Validators: [[458566](http://mainnet.beaconcha.in/validator/458566), [459103](http://mainnet.beaconcha.in/validator/459103)]\n\nslot: [6213852](https://mainnet.beaconcha.in/slot/6213852)',
    },
    {
        'summary': '🚨🚨🚨 2 Lido validators were slashed! 🚨🚨🚨',
        'description': '\nRockLogic GmbH - Violated duty: attester | Validators: [[458038](http://mainnet.beaconcha.in/validator/458038), [459803](http://mainnet.beaconcha.in/validator/459803)]\n\nslot: [6213853](https://mainnet.beaconcha.in/slot/6213853)',
    },
    {
        'summary': '🚨🚨🚨 2 Lido validators were slashed! 🚨🚨🚨',
        'description': '\nRockLogic GmbH - Violated duty: attester | Validators: [[459093](http://mainnet.beaconcha.in/validator/459093), [458562](http://mainnet.beaconcha.in/validator/458562)]\n\nslot: [6213854](https://mainnet.beaconcha.in/slot/6213854)',
    },
    {
        'summary': '🚨🚨🚨 2 Lido validators were slashed! 🚨🚨🚨',
        'description': '\nRockLogic GmbH - Violated duty: attester | Validators: [[458237](http://mainnet.beaconcha.in/validator/458237), [459225](http://mainnet.beaconcha.in/validator/459225)]\n\nslot: [6213855](https://mainnet.beaconcha.in/slot/6213855)',
    },
    {
        'summary': '🚨🚨🚨 2 Lido validators were slashed! 🚨🚨🚨',
        'description': '\nRockLogic GmbH - Violated duty: attester | Validators: [[459140](http://mainnet.beaconcha.in/validator/459140), [459098](http://mainnet.beaconcha.in/validator/459098)]\n\nslot: [6213856](https://mainnet.beaconcha.in/slot/6213856)',
    },
    {
        'summary': '🚨🚨🚨 1 Lido validators were slashed! 🚨🚨🚨',
        'description': '\nRockLogic GmbH - Violated duty: attester | Validators: [[459890](http://mainnet.beaconcha.in/validator/459890)]\n\nslot: [6213857](https://mainnet.beaconcha.in/slot/6213857)',
    },
]


def test_watcher(caplog, watcher):
    watcher.run()

    assert [h.header.message.slot for h in watcher.handled_headers] == [str(s) for s in range(6213851, 6213859)]

    assert watcher.keys_updater.done(), "Keys updater should be done"
    assert watcher.validators_updater.done(), "Validators updater should be done"

    assert len(watcher.lido_keys) > 228010, "Lido keys should be updated"
    assert len(watcher.indexed_validators_keys) > 785109, "Indexed validators keys should be updated"

    for alert in alerts:
        assert str(alert) in caplog.text, f"Alert {alert} should be in logs"
