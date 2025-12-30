def test_processing(watcher):
    watcher.run("6213851-6213858")

    assert [h.header.message.slot for h in watcher.handled_headers] == [str(s) for s in range(6213851, 6213859)]

    assert watcher.keys_updater.done(), "Keys updater should be done"
    assert watcher.validators_updater.done(), "Validators updater should be done"

    assert len(watcher.user_keys) > 228010, "Our keys should be updated"
    assert len(watcher.indexed_validators_keys) > 785109, "Indexed validators keys should be updated"


slashing_alerts = [
    {
        'summary': '🚨🚨🚨 2 Our validators were slashed! 🚨🚨🚨',
        'description': '\nRockLogic GmbH - Violated duty: attester | Validators: [[458566](http://mainnet.beaconcha.in/validator/458566), [459103](http://mainnet.beaconcha.in/validator/459103)]\n\nslot: [6213852](https://mainnet.beaconcha.in/slot/6213852)',
    },
    {
        'summary': '🚨🚨🚨 2 Our validators were slashed! 🚨🚨🚨',
        'description': '\nRockLogic GmbH - Violated duty: attester | Validators: [[458038](http://mainnet.beaconcha.in/validator/458038), [459803](http://mainnet.beaconcha.in/validator/459803)]\n\nslot: [6213853](https://mainnet.beaconcha.in/slot/6213853)',
    },
    {
        'summary': '🚨🚨🚨 2 Our validators were slashed! 🚨🚨🚨',
        'description': '\nRockLogic GmbH - Violated duty: attester | Validators: [[459093](http://mainnet.beaconcha.in/validator/459093), [458562](http://mainnet.beaconcha.in/validator/458562)]\n\nslot: [6213854](https://mainnet.beaconcha.in/slot/6213854)',
    },
    {
        'summary': '🚨🚨🚨 2 Our validators were slashed! 🚨🚨🚨',
        'description': '\nRockLogic GmbH - Violated duty: attester | Validators: [[458237](http://mainnet.beaconcha.in/validator/458237), [459225](http://mainnet.beaconcha.in/validator/459225)]\n\nslot: [6213855](https://mainnet.beaconcha.in/slot/6213855)',
    },
    {
        'summary': '🚨🚨🚨 2 Our validators were slashed! 🚨🚨🚨',
        'description': '\nRockLogic GmbH - Violated duty: attester | Validators: [[459140](http://mainnet.beaconcha.in/validator/459140), [459098](http://mainnet.beaconcha.in/validator/459098)]\n\nslot: [6213856](https://mainnet.beaconcha.in/slot/6213856)',
    },
    {
        'summary': '🚨🚨🚨 1 Our validators were slashed! 🚨🚨🚨',
        'description': '\nRockLogic GmbH - Violated duty: attester | Validators: [[459890](http://mainnet.beaconcha.in/validator/459890)]\n\nslot: [6213857](https://mainnet.beaconcha.in/slot/6213857)',
    },
]


def test_slashings(caplog, watcher):
    watcher.run("6213851-6213858")

    for alert in slashing_alerts:
        assert str(alert) in caplog.text, f"Alert {alert} should be in logs"


exit_alerts = [
    {
        'summary': '🚨🚨🚨 16 Our validators were unexpectedly exited! 🚨🚨🚨',
        'description': '\nA41 - [[1611864](http://mainnet.beaconcha.in/validator/1611864), [1596140](http://mainnet.beaconcha.in/validator/1596140), [1612125](http://mainnet.beaconcha.in/validator/1612125), [1611863](http://mainnet.beaconcha.in/validator/1611863), [1612123](http://mainnet.beaconcha.in/validator/1612123), [1611862](http://mainnet.beaconcha.in/validator/1611862), [1596139](http://mainnet.beaconcha.in/validator/1596139), [1595979](http://mainnet.beaconcha.in/validator/1595979), [1612124](http://mainnet.beaconcha.in/validator/1612124), [1612203](http://mainnet.beaconcha.in/validator/1612203), [1611710](http://mainnet.beaconcha.in/validator/1611710), [1595838](http://mainnet.beaconcha.in/validator/1595838), [1595978](http://mainnet.beaconcha.in/validator/1595978), [1611709](http://mainnet.beaconcha.in/validator/1611709), [1596138](http://mainnet.beaconcha.in/validator/1596138), [1595977](http://mainnet.beaconcha.in/validator/1595977)]\n\nslot: [13312726](https://mainnet.beaconcha.in/slot/13312726)',
    },
    {
        'summary': '🚨🚨🚨 16 Our validators were unexpectedly exited! 🚨🚨🚨',
        'description': '\nA41 - [[1612202](http://mainnet.beaconcha.in/validator/1612202), [1595837](http://mainnet.beaconcha.in/validator/1595837), [1616216](http://mainnet.beaconcha.in/validator/1616216), [1613042](http://mainnet.beaconcha.in/validator/1613042), [1645543](http://mainnet.beaconcha.in/validator/1645543), [1616427](http://mainnet.beaconcha.in/validator/1616427), [1595980](http://mainnet.beaconcha.in/validator/1595980), [1645500](http://mainnet.beaconcha.in/validator/1645500), [1634875](http://mainnet.beaconcha.in/validator/1634875), [1615856](http://mainnet.beaconcha.in/validator/1615856), [1596141](http://mainnet.beaconcha.in/validator/1596141), [1611711](http://mainnet.beaconcha.in/validator/1611711), [1595981](http://mainnet.beaconcha.in/validator/1595981), [1612503](http://mainnet.beaconcha.in/validator/1612503), [1611712](http://mainnet.beaconcha.in/validator/1611712), [1615857](http://mainnet.beaconcha.in/validator/1615857)]\n\nslot: [13312727](https://mainnet.beaconcha.in/slot/13312727)',
    },
]


def test_unexpected_exits(caplog, watcher):
    watcher.run("13312725-13312727")

    for alert in exit_alerts:
        assert str(alert) in caplog.text, f"Alert {alert} should be in logs"


# @todo Fix and uncomment these tests once new VEBO requests appear on Mainnet.
# def test_expected_exits(caplog, watcher):
#     watcher.run("6833022-6833039")
#
#     assert 'Our validators were unexpectedly exited!' not in caplog.text, "Alert should not be in logs"
#
#
# def test_disabled_alerts_exits(caplog, watcher, monkeypatch):
#     monkeypatch.setattr(watcher, "disable_unexpected_exit_alerts", ['3'])
#
#     watcher.run("11180702-11180703")
#
#     assert 'Our validators were unexpectedly exited!' not in caplog.text, "Alerts should not be in logs"
