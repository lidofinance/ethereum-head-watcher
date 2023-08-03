import pytest


def test_processing(watcher):
    watcher.run()

    assert [h.header.message.slot for h in watcher.handled_headers] == [str(s) for s in range(6213851, 6213859)]

    assert watcher.keys_updater.done(), "Keys updater should be done"
    assert watcher.validators_updater.done(), "Validators updater should be done"

    assert len(watcher.lido_keys) > 228010, "Lido keys should be updated"
    assert len(watcher.indexed_validators_keys) > 785109, "Indexed validators keys should be updated"


slashing_alerts = [
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


def test_slashings(caplog, watcher):
    with caplog.at_level("INFO"):
        watcher.run()

    for alert in slashing_alerts:
        assert str(alert) in caplog.text, f"Alert {alert} should be in logs"


exit_alerts = [
    {
        'summary': '🚨🚨🚨 16 Lido validators were unexpected exited! 🚨🚨🚨',
        'description': '\nConsensys -[[629209](http://mainnet.beaconcha.in/validator/629209), [614624](http://mainnet.beaconcha.in/validator/614624), [346858](http://mainnet.beaconcha.in/validator/346858), [628230](http://mainnet.beaconcha.in/validator/628230), [596256](http://mainnet.beaconcha.in/validator/596256), [696241](http://mainnet.beaconcha.in/validator/696241), [530129](http://mainnet.beaconcha.in/validator/530129), [530438](http://mainnet.beaconcha.in/validator/530438), [346318](http://mainnet.beaconcha.in/validator/346318), [530287](http://mainnet.beaconcha.in/validator/530287), [632200](http://mainnet.beaconcha.in/validator/632200), [625532](http://mainnet.beaconcha.in/validator/625532), [629381](http://mainnet.beaconcha.in/validator/629381), [630311](http://mainnet.beaconcha.in/validator/630311), [528148](http://mainnet.beaconcha.in/validator/528148), [587187](http://mainnet.beaconcha.in/validator/587187)]\n\nslot: [6897644](https://mainnet.beaconcha.in/slot/6897644)',
    },
    {
        'summary': '🚨🚨🚨 16 Lido validators were unexpected exited! 🚨🚨🚨',
        'description': '\nConsensys -[[455699](http://mainnet.beaconcha.in/validator/455699), [471219](http://mainnet.beaconcha.in/validator/471219), [515333](http://mainnet.beaconcha.in/validator/515333), [346662](http://mainnet.beaconcha.in/validator/346662), [396980](http://mainnet.beaconcha.in/validator/396980), [521400](http://mainnet.beaconcha.in/validator/521400), [506576](http://mainnet.beaconcha.in/validator/506576), [346678](http://mainnet.beaconcha.in/validator/346678), [346872](http://mainnet.beaconcha.in/validator/346872), [464257](http://mainnet.beaconcha.in/validator/464257), [346541](http://mainnet.beaconcha.in/validator/346541), [625530](http://mainnet.beaconcha.in/validator/625530), [535634](http://mainnet.beaconcha.in/validator/535634), [626204](http://mainnet.beaconcha.in/validator/626204), [456261](http://mainnet.beaconcha.in/validator/456261), [530442](http://mainnet.beaconcha.in/validator/530442)]\n\nslot: [6897645](https://mainnet.beaconcha.in/slot/6897645)',
    },
    {
        'summary': '🚨🚨🚨 16 Lido validators were unexpected exited! 🚨🚨🚨',
        'description': '\nConsensys -[[630305](http://mainnet.beaconcha.in/validator/630305), [667384](http://mainnet.beaconcha.in/validator/667384), [574028](http://mainnet.beaconcha.in/validator/574028), [628411](http://mainnet.beaconcha.in/validator/628411), [570867](http://mainnet.beaconcha.in/validator/570867), [628226](http://mainnet.beaconcha.in/validator/628226), [633090](http://mainnet.beaconcha.in/validator/633090), [730461](http://mainnet.beaconcha.in/validator/730461), [630301](http://mainnet.beaconcha.in/validator/630301), [520051](http://mainnet.beaconcha.in/validator/520051), [630313](http://mainnet.beaconcha.in/validator/630313), [621617](http://mainnet.beaconcha.in/validator/621617), [629500](http://mainnet.beaconcha.in/validator/629500), [632867](http://mainnet.beaconcha.in/validator/632867), [632574](http://mainnet.beaconcha.in/validator/632574), [632192](http://mainnet.beaconcha.in/validator/632192)]\n\nslot: [6897646](https://mainnet.beaconcha.in/slot/6897646)',
    },
    {
        'summary': '🚨🚨🚨 16 Lido validators were unexpected exited! 🚨🚨🚨',
        'description': '\nConsensys -[[527994](http://mainnet.beaconcha.in/validator/527994), [534910](http://mainnet.beaconcha.in/validator/534910), [577715](http://mainnet.beaconcha.in/validator/577715), [346721](http://mainnet.beaconcha.in/validator/346721), [530283](http://mainnet.beaconcha.in/validator/530283), [456195](http://mainnet.beaconcha.in/validator/456195), [520628](http://mainnet.beaconcha.in/validator/520628), [507845](http://mainnet.beaconcha.in/validator/507845), [455406](http://mainnet.beaconcha.in/validator/455406), [397205](http://mainnet.beaconcha.in/validator/397205), [630303](http://mainnet.beaconcha.in/validator/630303), [530291](http://mainnet.beaconcha.in/validator/530291), [562661](http://mainnet.beaconcha.in/validator/562661), [628234](http://mainnet.beaconcha.in/validator/628234), [534309](http://mainnet.beaconcha.in/validator/534309), [632198](http://mainnet.beaconcha.in/validator/632198)]\n\nslot: [6897647](https://mainnet.beaconcha.in/slot/6897647)',
    },
    {
        'summary': '🚨🚨🚨 16 Lido validators were unexpected exited! 🚨🚨🚨',
        'description': '\nConsensys -[[530279](http://mainnet.beaconcha.in/validator/530279), [696622](http://mainnet.beaconcha.in/validator/696622), [629052](http://mainnet.beaconcha.in/validator/629052), [530426](http://mainnet.beaconcha.in/validator/530426), [628224](http://mainnet.beaconcha.in/validator/628224), [630309](http://mainnet.beaconcha.in/validator/630309), [629050](http://mainnet.beaconcha.in/validator/629050), [632869](http://mainnet.beaconcha.in/validator/632869), [628228](http://mainnet.beaconcha.in/validator/628228), [632196](http://mainnet.beaconcha.in/validator/632196), [628232](http://mainnet.beaconcha.in/validator/628232), [633084](http://mainnet.beaconcha.in/validator/633084), [632572](http://mainnet.beaconcha.in/validator/632572), [691963](http://mainnet.beaconcha.in/validator/691963), [629478](http://mainnet.beaconcha.in/validator/629478), [632576](http://mainnet.beaconcha.in/validator/632576)]\n\nslot: [6897648](https://mainnet.beaconcha.in/slot/6897648)',
    },
    {
        'summary': '🚨🚨🚨 10 Lido validators were unexpected exited! 🚨🚨🚨',
        'description': '\nConsensys -[[632202](http://mainnet.beaconcha.in/validator/632202), [630307](http://mainnet.beaconcha.in/validator/630307), [703690](http://mainnet.beaconcha.in/validator/703690), [632194](http://mainnet.beaconcha.in/validator/632194), [651304](http://mainnet.beaconcha.in/validator/651304), [346271](http://mainnet.beaconcha.in/validator/346271), [632190](http://mainnet.beaconcha.in/validator/632190), [581412](http://mainnet.beaconcha.in/validator/581412), [530275](http://mainnet.beaconcha.in/validator/530275), [630315](http://mainnet.beaconcha.in/validator/630315)]\n\nslot: [6897649](https://mainnet.beaconcha.in/slot/6897649)',
    },
    {
        'summary': '🚨🚨🚨 9 Lido validators were unexpected exited! 🚨🚨🚨',
        'description': '\nConsensys -[[346599](http://mainnet.beaconcha.in/validator/346599), [530136](http://mainnet.beaconcha.in/validator/530136), [529832](http://mainnet.beaconcha.in/validator/529832), [346351](http://mainnet.beaconcha.in/validator/346351), [346761](http://mainnet.beaconcha.in/validator/346761), [457442](http://mainnet.beaconcha.in/validator/457442), [456821](http://mainnet.beaconcha.in/validator/456821), [529528](http://mainnet.beaconcha.in/validator/529528), [472676](http://mainnet.beaconcha.in/validator/472676)]\n\nslot: [6897652](https://mainnet.beaconcha.in/slot/6897652)',
    },
    {
        'summary': '🚨🚨🚨 16 Lido validators were unexpected exited! 🚨🚨🚨',
        'description': '\nConsensys -[[289852](http://mainnet.beaconcha.in/validator/289852), [530434](http://mainnet.beaconcha.in/validator/530434), [521577](http://mainnet.beaconcha.in/validator/521577), [404901](http://mainnet.beaconcha.in/validator/404901), [525681](http://mainnet.beaconcha.in/validator/525681), [532308](http://mainnet.beaconcha.in/validator/532308), [346315](http://mainnet.beaconcha.in/validator/346315), [534042](http://mainnet.beaconcha.in/validator/534042), [474371](http://mainnet.beaconcha.in/validator/474371), [554672](http://mainnet.beaconcha.in/validator/554672), [521183](http://mainnet.beaconcha.in/validator/521183), [555428](http://mainnet.beaconcha.in/validator/555428), [520043](http://mainnet.beaconcha.in/validator/520043), [535630](http://mainnet.beaconcha.in/validator/535630), [530577](http://mainnet.beaconcha.in/validator/530577), [482765](http://mainnet.beaconcha.in/validator/482765)]\n\nslot: [6897653](https://mainnet.beaconcha.in/slot/6897653)',
    },
    {
        'summary': '🚨🚨🚨 10 Lido validators were unexpected exited! 🚨🚨🚨',
        'description': '\nConsensys -[[457223](http://mainnet.beaconcha.in/validator/457223), [565725](http://mainnet.beaconcha.in/validator/565725), [346745](http://mainnet.beaconcha.in/validator/346745), [530430](http://mainnet.beaconcha.in/validator/530430), [456938](http://mainnet.beaconcha.in/validator/456938), [525339](http://mainnet.beaconcha.in/validator/525339), [289624](http://mainnet.beaconcha.in/validator/289624), [528614](http://mainnet.beaconcha.in/validator/528614), [554923](http://mainnet.beaconcha.in/validator/554923), [346766](http://mainnet.beaconcha.in/validator/346766)]\n\nslot: [6897654](https://mainnet.beaconcha.in/slot/6897654)',
    },
]


@pytest.mark.parametrize('slot_range_param', ["6897643-6897655"])
def test_unexpected_exits(caplog, watcher, slot_range_param):
    with caplog.at_level("INFO"):
        watcher.run()

    for alert in exit_alerts:
        assert str(alert) in caplog.text, f"Alert {alert} should be in logs"


@pytest.mark.parametrize('slot_range_param', ["6833022-6833039"])
def test_expected_exits(caplog, watcher, slot_range_param):
    with caplog.at_level("INFO"):
        watcher.run()

    assert 'Lido validators were unexpected exited!' not in caplog.text, "Alert should not be in logs"
