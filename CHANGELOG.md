# [0.6.0](https://github.com/lidofinance/ethereum-head-watcher/compare/0.5.0...0.6.0) (2026-07-13)


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



# [0.1.0](https://github.com/lidofinance/ethereum-head-watcher/compare/0b049a1e0307414919d37e831425faf285542b84...0.1.0) (2023-08-17)


### Bug Fixes

* add logs ([3f41892](https://github.com/lidofinance/ethereum-head-watcher/commit/3f41892394e97c84ca4a8499a29b83d2fd56cbc2))
* alerting ([#14](https://github.com/lidofinance/ethereum-head-watcher/issues/14)) ([ad506d2](https://github.com/lidofinance/ethereum-head-watcher/commit/ad506d21f6e885357998272736e53a22bd18d621))
* alerts ([#10](https://github.com/lidofinance/ethereum-head-watcher/issues/10)) ([2352e9e](https://github.com/lidofinance/ethereum-head-watcher/commit/2352e9ea36dc36d95ea4cb584d46a26060d3f41e))
* black ([6bf610f](https://github.com/lidofinance/ethereum-head-watcher/commit/6bf610fee43c6ddda070f31ee41873af4bb970ab))
* configs. multi-run ([7d240ef](https://github.com/lidofinance/ethereum-head-watcher/commit/7d240efd02debd10f9636e1895e1d250254061e2))
* configs. multi-run ([890e00d](https://github.com/lidofinance/ethereum-head-watcher/commit/890e00d685fdff3f6a87c5db023a92c9057f1b44))
* dict ([ea2571d](https://github.com/lidofinance/ethereum-head-watcher/commit/ea2571d7a8e5bbb2022bac889f1e6b191374e38b))
* dockerfile ([058cafe](https://github.com/lidofinance/ethereum-head-watcher/commit/058cafe1747f87ff2d62ee835a276e6f1b1e505a))
* errors ([f53c768](https://github.com/lidofinance/ethereum-head-watcher/commit/f53c7687c572d93fd44f51842b7bd01b1d3f3065))
* errors ([48589d3](https://github.com/lidofinance/ethereum-head-watcher/commit/48589d3528a3012002ad816e1e7de143dc85fd6c))
* HEALTHCHECK ([f11bb83](https://github.com/lidofinance/ethereum-head-watcher/commit/f11bb83ef13afe0fc6631931cf01aeee4a53dfff))
* isort ([25e2a67](https://github.com/lidofinance/ethereum-head-watcher/commit/25e2a672ca18e0ced6d694e7df6d51579ac61c08))
* labels ([b8678cc](https://github.com/lidofinance/ethereum-head-watcher/commit/b8678cc8441fa25da107d8f1cd97b701d6873c6c))
* mypy ([75f3e5d](https://github.com/lidofinance/ethereum-head-watcher/commit/75f3e5dd9edff993715c87e48657db45896b8c47))
* optimize ([1818512](https://github.com/lidofinance/ethereum-head-watcher/commit/18185129285e4bfc66b1cc6c5f854d89aeddecc3))
* parse validators ([#11](https://github.com/lidofinance/ethereum-head-watcher/issues/11)) ([cbe51e7](https://github.com/lidofinance/ethereum-head-watcher/commit/cbe51e7bfe6086cb4806987326151e1419fe0c53))
* remove comments ([19b0c7b](https://github.com/lidofinance/ethereum-head-watcher/commit/19b0c7b9546a237b1c4f37bf3127408cdf058534))
* review ([b934ba3](https://github.com/lidofinance/ethereum-head-watcher/commit/b934ba3f1d6a31362c4489400cdbe6bc4d86f3b8))
* review ([9276e88](https://github.com/lidofinance/ethereum-head-watcher/commit/9276e8864dfb3b61c46da39946f39a834952dc06))
* stable versions ([3b3468c](https://github.com/lidofinance/ethereum-head-watcher/commit/3b3468c03231926a8c70ce55f9b93b1fc08ee4cb))
* var ([ff14fcf](https://github.com/lidofinance/ethereum-head-watcher/commit/ff14fcf6b135ab00ce42ddb71d5f0ee54d98757b))
* workflow ([#13](https://github.com/lidofinance/ethereum-head-watcher/issues/13)) ([2ff5366](https://github.com/lidofinance/ethereum-head-watcher/commit/2ff5366866ce90fe5e697daad6999df4973b914e))


### Features

* additional labels ([e959d6f](https://github.com/lidofinance/ethereum-head-watcher/commit/e959d6fdfdd542f9b2b9c474aa265a0bffca2369))
* fork detection ([#6](https://github.com/lidofinance/ethereum-head-watcher/issues/6)) ([2d9ff46](https://github.com/lidofinance/ethereum-head-watcher/commit/2d9ff4604606a8c26de910a67a33cba64404c7b1))
* handle unexpected exits ([0732934](https://github.com/lidofinance/ethereum-head-watcher/commit/0732934f1eb9eea03a89f4042a1cbc60834522a4))
* health metrics alerts ([522464f](https://github.com/lidofinance/ethereum-head-watcher/commit/522464f4402091b244a24e5903db17a5cbc432ec))
* optimization ([40bbe32](https://github.com/lidofinance/ethereum-head-watcher/commit/40bbe32500d8fb6be31e78d13bf26cc00f8d218c))
* tests and polish ([#12](https://github.com/lidofinance/ethereum-head-watcher/issues/12)) ([5524e2c](https://github.com/lidofinance/ethereum-head-watcher/commit/5524e2c91dd8dd666033e91af3deedc5f1914e60))
* the very first version ([0b049a1](https://github.com/lidofinance/ethereum-head-watcher/commit/0b049a1e0307414919d37e831425faf285542b84))
* unknown index ([71967b0](https://github.com/lidofinance/ethereum-head-watcher/commit/71967b0305a94d93a72e4e09466cddb22b2071f0))



