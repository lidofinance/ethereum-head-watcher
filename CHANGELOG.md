# [0.9.0](https://github.com/lidofinance/ethereum-head-watcher/compare/0.8.0...0.9.0) (2026-11-15)


### Bug Fixes

* cast the event ABI to a plain dict for mypy ([c18fb60](https://github.com/lidofinance/ethereum-head-watcher/commit/c18fb6051f1ded19be6d7326cc4d1368fa2c019e))
* do not crash on an empty ADDITIONAL_ALERTMANAGER_LABELS ([83554fb](https://github.com/lidofinance/ethereum-head-watcher/commit/83554fb128ca80ae2676201b4f22679089ec8b42))
* do not crash when replaying a range of slots ([7d54a8c](https://github.com/lidofinance/ethereum-head-watcher/commit/7d54a8c6ee959a9dd41024ba07d545f2ffe4fc18))
* do not lose blocks and reorg events after a chain reorg ([9a5eb7d](https://github.com/lidofinance/ethereum-head-watcher/commit/9a5eb7d0ffd632a16c0b90cc819a8632848c09ca))
* fetch events by contract and apply consolidation removals only when finalized ([22986ab](https://github.com/lidofinance/ethereum-head-watcher/commit/22986ab6a23f8e6e7fe62cf0ed1743dea00b134f))
* incorrect execution payload endpoint ([5eee66c](https://github.com/lidofinance/ethereum-head-watcher/commit/5eee66c9a9d4f19a72cd9bd1ebcc348819ca4a08))
* make the Docker healthcheck detect a stuck watcher ([eed0f9e](https://github.com/lidofinance/ethereum-head-watcher/commit/eed0f9e6b6df724c688b241d7725db2fb219b88f))
* re-read last 64 blocks instead of tracking finalized block for consolidations ([ee8cb51](https://github.com/lidofinance/ethereum-head-watcher/commit/ee8cb51229293170edf95846772f15a9af0800b6))
* track consolidation batches by hash and re-read recent blocks ([a255493](https://github.com/lidofinance/ethereum-head-watcher/commit/a255493bce545c78e118c6d89361e55a8fdae256))
* **VROOM-545:** mask provider keys in CI logs by path, not only by whole URL ([5da6e9c](https://github.com/lidofinance/ethereum-head-watcher/commit/5da6e9c7b7bbff062e9ca53ded23ab57d2843984)), closes [#141](https://github.com/lidofinance/ethereum-head-watcher/issues/141)
* **VROOM-676:** attribute execution-layer RPC metrics to the endpoint that answered ([d266f5f](https://github.com/lidofinance/ethereum-head-watcher/commit/d266f5f4b9f3c2182314729f3c1248d834600b38))
* **VROOM-676:** handle no head before keys load, mask userinfo and named secrets ([b15a3e8](https://github.com/lidofinance/ethereum-head-watcher/commit/b15a3e8f295a883b82cb8a91aae1ed1b3c47bd97))
* **VROOM-676:** keep checkout build-info.json when no build args are passed ([5e093dc](https://github.com/lidofinance/ethereum-head-watcher/commit/5e093dc2c046b589e01436a4a9a9de2574db6ffe))
* **VROOM-676:** read the validator index once per epoch boundary while a head waits ([3d3a8ba](https://github.com/lidofinance/ethereum-head-watcher/commit/3d3a8ba305317bd7bd1f43b33ad2a279c89a124e))
* **VROOM-676:** satisfy mypy on event topic lookup ([d57374f](https://github.com/lidofinance/ethereum-head-watcher/commit/d57374f3013c3641d26488dcd84361e850460550))


### Features

* read Gloas execution requests from the parent envelope ([e3f5a61](https://github.com/lidofinance/ethereum-head-watcher/commit/e3f5a613b086395a1c60d75f59aaea4f1f153626))
* read the Gloas execution requests from the head block itself ([9630784](https://github.com/lidofinance/ethereum-head-watcher/commit/963078416a1192fb69cea61cd08573818e99e37b))
* tolerate Gloas (EIP-7732) block shape ([1c24d5f](https://github.com/lidofinance/ethereum-head-watcher/commit/1c24d5ffb604fc6dac18442fbea30df1ab151339))
* **VROOM-545:** run the watcher on Kubernetes again ([99f40f9](https://github.com/lidofinance/ethereum-head-watcher/commit/99f40f970b1973a01fc02d43a2bbc81d39a1bd22)), closes [#141](https://github.com/lidofinance/ethereum-head-watcher/issues/141) [#149](https://github.com/lidofinance/ethereum-head-watcher/issues/149) [#141](https://github.com/lidofinance/ethereum-head-watcher/issues/141) [#141](https://github.com/lidofinance/ethereum-head-watcher/issues/141)
* **VROOM-676:** log redaction, build-info, slim image, RPC metrics ([4c35ac9](https://github.com/lidofinance/ethereum-head-watcher/commit/4c35ac931bc6873da3f852f72c1d543d601c3f10))



# [0.8.0](https://github.com/lidofinance/ethereum-head-watcher/compare/0.7.0...0.8.0) (2026-09-18)


### Bug Fixes

* keep provider credentials out of the logs ([b1aae62](https://github.com/lidofinance/ethereum-head-watcher/commit/b1aae62028069653919eae1e85a7f580ffb405fc))
* linter issues ([d6bc67e](https://github.com/lidofinance/ethereum-head-watcher/commit/d6bc67e90e27768a47d4fddc22e7fb01dd844be1))
* name the failing provider by position, not by host ([e06f5f1](https://github.com/lidofinance/ethereum-head-watcher/commit/e06f5f139398d8e48859bd4e9e39a2cc37541a1b))
* replace slot number with state root ([5f90815](https://github.com/lidofinance/ethereum-head-watcher/commit/5f90815a6c45f0760ef23ccc1fbd38aab26b9ebf))
* say where the configuration came from ([16cf775](https://github.com/lidofinance/ethereum-head-watcher/commit/16cf77531bfe4ff737ecc4cb891f152ff497e036))
* stop on SIGTERM instead of waiting out the pod grace period ([ffec629](https://github.com/lidofinance/ethereum-head-watcher/commit/ffec629a1f90546e5b81ce752b0e3bf69da45ab7))
* tests ([2fb5104](https://github.com/lidofinance/ethereum-head-watcher/commit/2fb51041fdb5dbc1ef2244e84ff40bedca903cb6))
* tests ([3073901](https://github.com/lidofinance/ethereum-head-watcher/commit/3073901098cf2e75abd65ba1c5826264fc563b25))
* update dependencies in Dockerfile ([0b8979b](https://github.com/lidofinance/ethereum-head-watcher/commit/0b8979bb1588607e7fac9b9032a687cf72cb7334))


### Features

* add Slack support ([13db474](https://github.com/lidofinance/ethereum-head-watcher/commit/13db47463cca675cd614832a9f48b26637571df9))
* read-only health endpoints for k8s probes ([f2c084a](https://github.com/lidofinance/ethereum-head-watcher/commit/f2c084aecfa80029aafbcdf2fc3f519c62f57031))
* report a rotated setting no live apply reaches, and the mtime of the file in force ([7ad516f](https://github.com/lidofinance/ethereum-head-watcher/commit/7ad516fad866468469cfe0c8ee988246af51a3b9))
* **vroom-546:** read node endpoints from a secrets file and reload on rotation ([c358466](https://github.com/lidofinance/ethereum-head-watcher/commit/c358466e1c27d5e9a17d32f3c9a909916e26bea2))
* workflow ([e00d51c](https://github.com/lidofinance/ethereum-head-watcher/commit/e00d51c2694f8dc4acafb97ab8ed8a345c144dc1))



# [0.7.0](https://github.com/lidofinance/ethereum-head-watcher/compare/0.6.0...0.7.0) (2026-08-07)


### Bug Fixes

* defer enabled handler validation to startup ([40d8016](https://github.com/lidofinance/ethereum-head-watcher/commit/40d80164414b26100f95f343463862e0028cd009))


### Features

* add configurable handler selection ([e0e8e18](https://github.com/lidofinance/ethereum-head-watcher/commit/e0e8e18e29f19118258c9e5c9f91bd1caf64d961))



# [0.6.0](https://github.com/lidofinance/ethereum-head-watcher/compare/0.5.0...0.6.0) (2026-07-14)


### Bug Fixes

* check existence of modules-operators dict ([5860317](https://github.com/lidofinance/ethereum-head-watcher/commit/58603171048aab219419d07f03ae972304ae48ad))
* description of alert about incorrect status ([ddf230f](https://github.com/lidofinance/ethereum-head-watcher/commit/ddf230f40e9b6de1b3304f7c6059d36e3454a496))
* elements in `ConsolidationBatchItem` class ([143a31a](https://github.com/lidofinance/ethereum-head-watcher/commit/143a31a51148ffc1102efb418fc44883a9cc31b9))
* imports order ([fd22632](https://github.com/lidofinance/ethereum-head-watcher/commit/fd226325beea6364f156950877570287bcd3687a))
* incorrect consolidation batch parsing ([9c2fc9d](https://github.com/lidofinance/ethereum-head-watcher/commit/9c2fc9d2b3d595d7b3a3b82c010cd536da459645))
* invalid consolidation status alert ([beff8f8](https://github.com/lidofinance/ethereum-head-watcher/commit/beff8f84bfe06e88a95e547f0377b0d24e90bad5))
* issue in conversion of bytes pubkeys ([4bb2825](https://github.com/lidofinance/ethereum-head-watcher/commit/4bb282554d5ef2ca680d0b3cc2af4bd7bee30074))
* issues in last unit tests ([cb36a65](https://github.com/lidofinance/ethereum-head-watcher/commit/cb36a65d05d25d907274216018247e4a41c79367))
* linter errors ([19f4354](https://github.com/lidofinance/ethereum-head-watcher/commit/19f43542af69b8494313d1a348d5b15030e5dc23))
* linter issues ([e430d5e](https://github.com/lidofinance/ethereum-head-watcher/commit/e430d5e411707973ae68b2a91481fec864f6b1f8))
* linter issues ([2ba6c92](https://github.com/lidofinance/ethereum-head-watcher/commit/2ba6c92ac3031b666fd9cfe82927a86b0f5f6156))
* linter issues ([2778618](https://github.com/lidofinance/ethereum-head-watcher/commit/277861813804ecb5fed1c07e9f34dcfb7100ca09))
* linter issues ([8599ebf](https://github.com/lidofinance/ethereum-head-watcher/commit/8599ebf5782fe0ce8a3ddee12d68223d278e75cf))
* linter issues ([a4b7ea0](https://github.com/lidofinance/ethereum-head-watcher/commit/a4b7ea05dce3bcdca1adfd4bf3cf36264f56c5dd))
* linter issues ([cd2ee00](https://github.com/lidofinance/ethereum-head-watcher/commit/cd2ee00628fa424cc493e2c7d9467fdbef890f18))
* linter issues ([6a06b3f](https://github.com/lidofinance/ethereum-head-watcher/commit/6a06b3f416232e8435ced6256195d5ab5935e90c))
* migrate ValidatorStatus to StrEnum ([54f773d](https://github.com/lidofinance/ethereum-head-watcher/commit/54f773daa85e80e1bf242c29777c607de5c71d65))
* minor issue in utils method ([92306c8](https://github.com/lidofinance/ethereum-head-watcher/commit/92306c8947767c41b777651a621a69907b29c7e3))
* minor issues in unit tests ([b480054](https://github.com/lidofinance/ethereum-head-watcher/commit/b4800542e5303414d46f3bed761621f5d4ceabc2))
* name of test validator ([544f272](https://github.com/lidofinance/ethereum-head-watcher/commit/544f2729748485995e7a3b48716c1d1807afbeef))
* remove unnecessary type ([e15a87c](https://github.com/lidofinance/ethereum-head-watcher/commit/e15a87ce1eb023ad4a9d45fe6f2f6492db0cee53))
* unexpected exit tests ([227a8da](https://github.com/lidofinance/ethereum-head-watcher/commit/227a8da48869d2f13037e4e7a7d7126516bd7ff0))


### Features

* alert for consolidation with requested exit ([2079cd4](https://github.com/lidofinance/ethereum-head-watcher/commit/2079cd45beccbba22a937e4f8290806799a1cd8e))
* alert for exits with requested consolidation ([39cdb2a](https://github.com/lidofinance/ethereum-head-watcher/commit/39cdb2ad928bdad9cd34b7aa3cbcd68e648126d9))
* consolidation alerts from our WA ([e2d8f0d](https://github.com/lidofinance/ethereum-head-watcher/commit/e2d8f0d03e574d05d5a82eb72f0e66728717c888))
* invalid statuses consolidation alert ([28c4d2f](https://github.com/lidofinance/ethereum-head-watcher/commit/28c4d2febadb1e7d27f959fe2584b8455e9b0c71))
* over deposit consolidation alert ([1e6fe3c](https://github.com/lidofinance/ethereum-head-watcher/commit/1e6fe3c161be837b8c6eb3fdb730866dfa6b5459))
* rejected consolidation alert ([d1bcd61](https://github.com/lidofinance/ethereum-head-watcher/commit/d1bcd61a826e77a110ba9f5d92b2dffc24b346b6))



# [0.5.0](https://github.com/lidofinance/ethereum-head-watcher/compare/0.4.0...0.5.0) (2025-12-31)


### Bug Fixes

* bug in `get_events_in_range` function call ([0033430](https://github.com/lidofinance/ethereum-head-watcher/commit/0033430aa8d20abca7ddc00b183dda6fb2c8a68b))
* bugs in new unexpected exit processing algorithm ([2548487](https://github.com/lidofinance/ethereum-head-watcher/commit/254848712b7e36de7587f43a0e9c7f5c39c07a52))
* e2e tests for unexpected exit alerts ([b6f17db](https://github.com/lidofinance/ethereum-head-watcher/commit/b6f17db3f7763ddd66e649824860f0e755d82c82))
* linter errors ([bb51702](https://github.com/lidofinance/ethereum-head-watcher/commit/bb51702af695b4064e2cb79c4b144c2a7c6b5e2e))
* linter errors ([2e341e3](https://github.com/lidofinance/ethereum-head-watcher/commit/2e341e35fdfb0a2cf176f49f7e247159327bbe5d))
* missing parentheses ([2335f31](https://github.com/lidofinance/ethereum-head-watcher/commit/2335f317c715c0727471017a3f5ea8378d6f88c7))
* review comments and lint issues ([26b9530](https://github.com/lidofinance/ethereum-head-watcher/commit/26b953053567cad182b3453528287c750068be9b))
* unexpected exits alert ([ac185a4](https://github.com/lidofinance/ethereum-head-watcher/commit/ac185a40a0c0a2198eb3b2a374fd1c6d468620a6))


### Features

* add env variable for `eth_getLogs` method calls ([4d59ef2](https://github.com/lidofinance/ethereum-head-watcher/commit/4d59ef29ecd77b4017970200c4f9fc3de7eb60ea))



# [0.4.0](https://github.com/lidofinance/ethereum-head-watcher/compare/0.3.1...0.4.0) (2025-10-30)


### Features

* handle EIP-7002 semantics for withdrawals ([#101](https://github.com/lidofinance/ethereum-head-watcher/issues/101)) ([e4c1a1b](https://github.com/lidofinance/ethereum-head-watcher/commit/e4c1a1b18b07637fa084b1193919356aa3c9a1f0))



## [0.3.1](https://github.com/lidofinance/ethereum-head-watcher/compare/0.3.0...0.3.1) (2025-06-24)


### Bug Fixes

* replace curl with python in healthcheck ([#79](https://github.com/lidofinance/ethereum-head-watcher/issues/79)) ([ab8378f](https://github.com/lidofinance/ethereum-head-watcher/commit/ab8378f5c08a6053d948d2fc48c281efcc7e3f93))


### Reverts

* Revert "chore(deps): bump eth-abi from 4.1.0 to 5.0.1 (#70)" (#86) ([2086d96](https://github.com/lidofinance/ethereum-head-watcher/commit/2086d9639cec959d3e4401950e47e18b7495cd11)), closes [#70](https://github.com/lidofinance/ethereum-head-watcher/issues/70) [#86](https://github.com/lidofinance/ethereum-head-watcher/issues/86)



# [0.3.0](https://github.com/lidofinance/ethereum-head-watcher/compare/0.2.1...0.3.0) (2025-04-07)


### Bug Fixes

* typo in Dockerfile HEALTHCHECK_SERVER_PORT ([#59](https://github.com/lidofinance/ethereum-head-watcher/issues/59)) ([8bdf046](https://github.com/lidofinance/ethereum-head-watcher/commit/8bdf046d8f45d90105dd050b899b345b2cf656f6))


### Features

* add support for disabling unexpected exit alerts per module ([#60](https://github.com/lidofinance/ethereum-head-watcher/issues/60)) ([73f7fde](https://github.com/lidofinance/ethereum-head-watcher/commit/73f7fdebacfc0f6c759540ac21531d10fde10198))
* workflows adjustments for hoodi/holesky deployments ([c3b4839](https://github.com/lidofinance/ethereum-head-watcher/commit/c3b4839d5a15e158a3ce0b970be7364958fa7515))



## [0.2.1](https://github.com/lidofinance/ethereum-head-watcher/compare/0.2.0...0.2.1) (2024-08-13)


### Bug Fixes

* adjusted secret variable name in test&checks workflow ([c4a59c4](https://github.com/lidofinance/ethereum-head-watcher/commit/c4a59c427420a4917866d1cd42bd203c8fa86316))
* curl version ([7d7b994](https://github.com/lidofinance/ethereum-head-watcher/commit/7d7b9946e074549e7fba791bcfc5fa4ebe2a0c1e))
* incorrect curl version ([4641d9a](https://github.com/lidofinance/ethereum-head-watcher/commit/4641d9a6bcbaaa521524c05d29feec9206a1546b))
* incorrect curl version ([412b786](https://github.com/lidofinance/ethereum-head-watcher/commit/412b7865d18204c2b2ad77f194ae8f441d54dde5))
* incorrect env variable name ([3c6124a](https://github.com/lidofinance/ethereum-head-watcher/commit/3c6124ac22b37a311290e1fc43cba6333ee4cc48))



# [0.2.0](https://github.com/lidofinance/ethereum-head-watcher/compare/0.1.0...0.2.0) (2023-09-07)


### Bug Fixes

* isort ([6fbbc5b](https://github.com/lidofinance/ethereum-head-watcher/commit/6fbbc5b5644b215f968857760a920ee06c0953f5))
* mypy ([a8d3948](https://github.com/lidofinance/ethereum-head-watcher/commit/a8d3948ea00b75e96dc669aed6cb97658997f27b))
* test ([f0e1201](https://github.com/lidofinance/ethereum-head-watcher/commit/f0e120169c24816dde80727fb2ec8f7691dd0447))


### Features

* custom validators list ([fb81bcb](https://github.com/lidofinance/ethereum-head-watcher/commit/fb81bcb7f1255ac5ecd37dc07b275cf31a5445f5))



