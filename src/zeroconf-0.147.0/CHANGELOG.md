# CHANGELOG


## v0.147.0 (2025-05-03)

### Features

- Add cython 3.1 support ([#1580](https://github.com/python-zeroconf/python-zeroconf/pull/1580),
  [`1d9c94a`](https://github.com/python-zeroconf/python-zeroconf/commit/1d9c94a82d8da16b8f5355131e6167b69293da6c))

- Cython 3.1 support ([#1578](https://github.com/python-zeroconf/python-zeroconf/pull/1578),
  [`daaf8d6`](https://github.com/python-zeroconf/python-zeroconf/commit/daaf8d6981c778fe4ba0a63371d9368cf217891a))

- Cython 3.11 support ([#1579](https://github.com/python-zeroconf/python-zeroconf/pull/1579),
  [`1569383`](https://github.com/python-zeroconf/python-zeroconf/commit/1569383c6cf8ce8977427cfdaf5c7104ce52ab08))


## v0.146.5 (2025-04-14)

### Bug Fixes

- Address non-working socket configuration
  ([#1563](https://github.com/python-zeroconf/python-zeroconf/pull/1563),
  [`cc0f835`](https://github.com/python-zeroconf/python-zeroconf/commit/cc0f8350c30c82409b1a9bfecb19ff9b3368d6a7))

Co-authored-by: J. Nick Koston <nick@koston.org>


## v0.146.4 (2025-04-14)

### Bug Fixes

- Avoid loading adapter list twice
  ([#1564](https://github.com/python-zeroconf/python-zeroconf/pull/1564),
  [`8359488`](https://github.com/python-zeroconf/python-zeroconf/commit/83594887521507cf77bfc0a397becabaaab287c2))


## v0.146.3 (2025-04-02)

### Bug Fixes

- Correctly override question type flag for requests
  ([#1558](https://github.com/python-zeroconf/python-zeroconf/pull/1558),
  [`bd643a2`](https://github.com/python-zeroconf/python-zeroconf/commit/bd643a227bc4d6a949d558850ad1431bc2940d74))

* fix: correctly override question type flag for requests

Currently even when setting the explicit question type flag, the implementation ignores it for
  subsequent queries. This commit ensures that all queries respect the explicit question type flag.

* chore(tests): add test for explicit question type flag

Add unit test to validate that the explicit question type flag is set correctly in outgoing
  requests.


## v0.146.2 (2025-04-01)

### Bug Fixes

- Create listener socket with specific IP version
  ([#1557](https://github.com/python-zeroconf/python-zeroconf/pull/1557),
  [`b757ddf`](https://github.com/python-zeroconf/python-zeroconf/commit/b757ddf98d7d04c366281a4281a449c5c2cb897d))

* fix: create listener socket with specific IP version

Create listener sockets when using unicast with specific IP version as well, just like in
  `new_respond_socket()`.

* chore(tests): add unit test for socket creation with unicast addressing


## v0.146.1 (2025-03-05)

### Bug Fixes

- Use trusted publishing for uploading wheels
  ([#1541](https://github.com/python-zeroconf/python-zeroconf/pull/1541),
  [`fa65cc8`](https://github.com/python-zeroconf/python-zeroconf/commit/fa65cc8791a6f4c53bc29088cb60b83f420b1ae6))


## v0.146.0 (2025-03-05)

### Features

- Reduce size of wheels ([#1540](https://github.com/python-zeroconf/python-zeroconf/pull/1540),
  [`dea233c`](https://github.com/python-zeroconf/python-zeroconf/commit/dea233c1e0e80584263090727ce07648755964af))

feat: reduce size of binaries


## v0.145.1 (2025-02-18)

### Bug Fixes

- Hold a strong reference to the AsyncEngine setup task
  ([#1533](https://github.com/python-zeroconf/python-zeroconf/pull/1533),
  [`d4e6f25`](https://github.com/python-zeroconf/python-zeroconf/commit/d4e6f25754c15417b8bd9839dc8636b2cff717c8))


## v0.145.0 (2025-02-15)

### Features

- **docs**: Enable link to source code
  ([#1529](https://github.com/python-zeroconf/python-zeroconf/pull/1529),
  [`1c7f354`](https://github.com/python-zeroconf/python-zeroconf/commit/1c7f3548b6cbddf73dbb9d69cd8987c8ad32c705))


## v0.144.3 (2025-02-14)

### Bug Fixes

- Non unique name during wheel upload
  ([#1527](https://github.com/python-zeroconf/python-zeroconf/pull/1527),
  [`43136fa`](https://github.com/python-zeroconf/python-zeroconf/commit/43136fa418d4d7826415e1d0f7761b198347ced7))


## v0.144.2 (2025-02-14)

### Bug Fixes

- Add a helpful hint for when EADDRINUSE happens during startup
  ([#1526](https://github.com/python-zeroconf/python-zeroconf/pull/1526),
  [`48dbb71`](https://github.com/python-zeroconf/python-zeroconf/commit/48dbb7190a4f5126e39dbcdb87e34380d4562cd0))


## v0.144.1 (2025-02-12)

### Bug Fixes

- Wheel builds failing after adding armv7l builds
  ([#1518](https://github.com/python-zeroconf/python-zeroconf/pull/1518),
  [`e7adac9`](https://github.com/python-zeroconf/python-zeroconf/commit/e7adac9c59fc4d0c4822c6097a4daee3d68eb4de))


## v0.144.0 (2025-02-12)

### Features

- Add armv7l wheel builds ([#1517](https://github.com/python-zeroconf/python-zeroconf/pull/1517),
  [`39887b8`](https://github.com/python-zeroconf/python-zeroconf/commit/39887b80328d616e8e6f6ca9d08aecc06f7b0711))


## v0.143.1 (2025-02-12)

### Bug Fixes

- Make no buffer space available when adding multicast memberships forgiving
  ([#1516](https://github.com/python-zeroconf/python-zeroconf/pull/1516),
  [`f377d5c`](https://github.com/python-zeroconf/python-zeroconf/commit/f377d5cd08d724282c8487785163b466f3971344))


## v0.143.0 (2025-01-31)

### Features

- Eliminate async_timeout dep on python less than 3.11
  ([#1500](https://github.com/python-zeroconf/python-zeroconf/pull/1500),
  [`44457be`](https://github.com/python-zeroconf/python-zeroconf/commit/44457be4571add2f851192db3b37a96d9d27b00e))


## v0.142.0 (2025-01-30)

### Features

- Add simple address resolvers and examples
  ([#1499](https://github.com/python-zeroconf/python-zeroconf/pull/1499),
  [`ae3c352`](https://github.com/python-zeroconf/python-zeroconf/commit/ae3c3523e5f2896989d0b932d53ef1e24ef4aee8))


## v0.141.0 (2025-01-22)

### Features

- Speed up adding and expiring records in the DNSCache
  ([#1490](https://github.com/python-zeroconf/python-zeroconf/pull/1490),
  [`628b136`](https://github.com/python-zeroconf/python-zeroconf/commit/628b13670d04327dd8d4908842f31b476598c7e8))


## v0.140.1 (2025-01-17)

### Bug Fixes

- Wheel builds for aarch64 ([#1485](https://github.com/python-zeroconf/python-zeroconf/pull/1485),
  [`9d228e2`](https://github.com/python-zeroconf/python-zeroconf/commit/9d228e28eead1561deda696e8837d59896cbc98d))


## v0.140.0 (2025-01-17)

### Bug Fixes

- **docs**: Remove repetition of words
  ([#1479](https://github.com/python-zeroconf/python-zeroconf/pull/1479),
  [`dde26c6`](https://github.com/python-zeroconf/python-zeroconf/commit/dde26c655a49811c11071b0531e408a188687009))

Co-authored-by: J. Nick Koston <nick@koston.org>

### Features

- Migrate to native types ([#1472](https://github.com/python-zeroconf/python-zeroconf/pull/1472),
  [`22a0fb4`](https://github.com/python-zeroconf/python-zeroconf/commit/22a0fb487db27bc2c6448a9167742f3040e910ba))

Co-authored-by: J. Nick Koston <nick@koston.org>

Co-authored-by: pre-commit-ci[bot] <66853113+pre-commit-ci[bot]@users.noreply.github.com>

- Small performance improvement to writing outgoing packets
  ([#1482](https://github.com/python-zeroconf/python-zeroconf/pull/1482),
  [`d9be715`](https://github.com/python-zeroconf/python-zeroconf/commit/d9be7155a0ef1ac521e5bbedd3884ddeb9f0b99d))


## v0.139.0 (2025-01-09)

### Features

- Implement heapq for tracking cache expire times
  ([#1465](https://github.com/python-zeroconf/python-zeroconf/pull/1465),
  [`09db184`](https://github.com/python-zeroconf/python-zeroconf/commit/09db1848957b34415f364b7338e4adce99b57abc))


## v0.138.1 (2025-01-08)

### Bug Fixes

- Ensure cache does not return stale created and ttl values
  ([#1469](https://github.com/python-zeroconf/python-zeroconf/pull/1469),
  [`e05055c`](https://github.com/python-zeroconf/python-zeroconf/commit/e05055c584ca46080990437b2b385a187bc48458))


## v0.138.0 (2025-01-08)

### Features

- Improve performance of processing incoming records
  ([#1467](https://github.com/python-zeroconf/python-zeroconf/pull/1467),
  [`ebbb2af`](https://github.com/python-zeroconf/python-zeroconf/commit/ebbb2afccabd3841a3cb0a39824b49773cc6258a))

Co-authored-by: pre-commit-ci[bot] <66853113+pre-commit-ci[bot]@users.noreply.github.com>


## v0.137.2 (2025-01-06)

### Bug Fixes

- Split wheel builds to avoid timeout
  ([#1461](https://github.com/python-zeroconf/python-zeroconf/pull/1461),
  [`be05f0d`](https://github.com/python-zeroconf/python-zeroconf/commit/be05f0dc4f6b2431606031a7bb24585728d15f01))


## v0.137.1 (2025-01-06)

### Bug Fixes

- Move wheel builds to macos-13
  ([#1459](https://github.com/python-zeroconf/python-zeroconf/pull/1459),
  [`4ff48a0`](https://github.com/python-zeroconf/python-zeroconf/commit/4ff48a01bc76c82e5710aafaf6cf6e79c069cd85))


## v0.137.0 (2025-01-06)

### Features

- Speed up parsing incoming records
  ([#1458](https://github.com/python-zeroconf/python-zeroconf/pull/1458),
  [`783c1b3`](https://github.com/python-zeroconf/python-zeroconf/commit/783c1b37d1372c90dfce658c66d03aa753afbf49))


## v0.136.2 (2024-11-21)

### Bug Fixes

- Retrigger release from failed github workflow
  ([#1443](https://github.com/python-zeroconf/python-zeroconf/pull/1443),
  [`2ea705d`](https://github.com/python-zeroconf/python-zeroconf/commit/2ea705d850c1cb096c87372d5ec855f684603d01))


## v0.136.1 (2024-11-21)

### Bug Fixes

- **ci**: Run release workflow only on main repository
  ([#1441](https://github.com/python-zeroconf/python-zeroconf/pull/1441),
  [`f637c75`](https://github.com/python-zeroconf/python-zeroconf/commit/f637c75f638ba20c193e58ff63c073a4003430b9))

- **docs**: Update python to 3.8
  ([#1430](https://github.com/python-zeroconf/python-zeroconf/pull/1430),
  [`483d067`](https://github.com/python-zeroconf/python-zeroconf/commit/483d0673d4ae3eec37840452723fc1839a6cc95c))


## v0.136.0 (2024-10-26)

### Bug Fixes

- Add ignore for .c file for wheels
  ([#1424](https://github.com/python-zeroconf/python-zeroconf/pull/1424),
  [`6535963`](https://github.com/python-zeroconf/python-zeroconf/commit/6535963b5b789ce445e77bb728a5b7ee4263e582))

- Correct typos ([#1422](https://github.com/python-zeroconf/python-zeroconf/pull/1422),
  [`3991b42`](https://github.com/python-zeroconf/python-zeroconf/commit/3991b4256b8de5b37db7a6144e5112f711b2efef))

- Update python-semantic-release to fix release process
  ([#1426](https://github.com/python-zeroconf/python-zeroconf/pull/1426),
  [`2f20155`](https://github.com/python-zeroconf/python-zeroconf/commit/2f201558d0ab089cdfebb18d2d7bb5785b2cce16))

### Features

- Use SPDX license identifier
  ([#1425](https://github.com/python-zeroconf/python-zeroconf/pull/1425),
  [`1596145`](https://github.com/python-zeroconf/python-zeroconf/commit/1596145452721e0de4e2a724b055e8e290792d3e))


## v0.135.0 (2024-09-24)

### Features

- Improve performance of DNSCache backend
  ([#1415](https://github.com/python-zeroconf/python-zeroconf/pull/1415),
  [`1df2e69`](https://github.com/python-zeroconf/python-zeroconf/commit/1df2e691ff11c9592e1cdad5599fb6601eb1aa3f))


## v0.134.0 (2024-09-08)

### Bug Fixes

- Improve helpfulness of ServiceInfo.request assertions
  ([#1408](https://github.com/python-zeroconf/python-zeroconf/pull/1408),
  [`9262626`](https://github.com/python-zeroconf/python-zeroconf/commit/9262626895d354ed7376aa567043b793c37a985e))

### Features

- Improve performance when IP addresses change frequently
  ([#1407](https://github.com/python-zeroconf/python-zeroconf/pull/1407),
  [`111c91a`](https://github.com/python-zeroconf/python-zeroconf/commit/111c91ab395a7520e477eb0e75d5924fba3c64c7))


## v0.133.0 (2024-08-27)

### Features

- Add classifier for python 3.13
  ([#1393](https://github.com/python-zeroconf/python-zeroconf/pull/1393),
  [`7fb2bb2`](https://github.com/python-zeroconf/python-zeroconf/commit/7fb2bb21421c70db0eb288fa7e73d955f58b0f5d))

- Enable building of arm64 macOS builds
  ([#1384](https://github.com/python-zeroconf/python-zeroconf/pull/1384),
  [`0df2ce0`](https://github.com/python-zeroconf/python-zeroconf/commit/0df2ce0e6f7313831da6a63d477019982d5df55c))

Co-authored-by: Alex Ciobanu <alex@rogue-research.com>

Co-authored-by: J. Nick Koston <nick@koston.org>

- Improve performance of ip address caching
  ([#1392](https://github.com/python-zeroconf/python-zeroconf/pull/1392),
  [`f7c7708`](https://github.com/python-zeroconf/python-zeroconf/commit/f7c77081b2f8c70b1ed6a9b9751a86cf91f9aae2))

- Python 3.13 support ([#1390](https://github.com/python-zeroconf/python-zeroconf/pull/1390),
  [`98cfa83`](https://github.com/python-zeroconf/python-zeroconf/commit/98cfa83710e43880698353821bae61108b08cb2f))


## v0.132.2 (2024-04-13)

### Bug Fixes

- Bump cibuildwheel to fix wheel builds
  ([#1371](https://github.com/python-zeroconf/python-zeroconf/pull/1371),
  [`83e4ce3`](https://github.com/python-zeroconf/python-zeroconf/commit/83e4ce3e31ddd4ae9aec2f8c9d84d7a93f8be210))

- Update references to minimum-supported python version of 3.8
  ([#1369](https://github.com/python-zeroconf/python-zeroconf/pull/1369),
  [`599524a`](https://github.com/python-zeroconf/python-zeroconf/commit/599524a5ce1e4c1731519dd89377c2a852e59935))


## v0.132.1 (2024-04-12)

### Bug Fixes

- Set change during iteration when dispatching listeners
  ([#1370](https://github.com/python-zeroconf/python-zeroconf/pull/1370),
  [`e9f8aa5`](https://github.com/python-zeroconf/python-zeroconf/commit/e9f8aa5741ae2d490c33a562b459f0af1014dbb0))


## v0.132.0 (2024-04-01)

### Bug Fixes

- Avoid including scope_id in IPv6Address object if its zero
  ([#1367](https://github.com/python-zeroconf/python-zeroconf/pull/1367),
  [`edc4a55`](https://github.com/python-zeroconf/python-zeroconf/commit/edc4a556819956c238a11332052000dcbcb07e3d))

### Features

- Drop python 3.7 support ([#1359](https://github.com/python-zeroconf/python-zeroconf/pull/1359),
  [`4877829`](https://github.com/python-zeroconf/python-zeroconf/commit/4877829e6442de5426db152d11827b1ba85dbf59))

- Make async_get_service_info available on the Zeroconf object
  ([#1366](https://github.com/python-zeroconf/python-zeroconf/pull/1366),
  [`c4c2dee`](https://github.com/python-zeroconf/python-zeroconf/commit/c4c2deeb05279ddbb0eba1330c7ae58795fea001))


## v0.131.0 (2023-12-19)

### Features

- Small speed up to constructing outgoing packets
  ([#1354](https://github.com/python-zeroconf/python-zeroconf/pull/1354),
  [`517d7d0`](https://github.com/python-zeroconf/python-zeroconf/commit/517d7d00ca7738c770077738125aec0e4824c000))

- Speed up processing incoming packets
  ([#1352](https://github.com/python-zeroconf/python-zeroconf/pull/1352),
  [`6c15325`](https://github.com/python-zeroconf/python-zeroconf/commit/6c153258a995cf9459a6f23267b7e379b5e2550f))

- Speed up the query handler ([#1350](https://github.com/python-zeroconf/python-zeroconf/pull/1350),
  [`9eac0a1`](https://github.com/python-zeroconf/python-zeroconf/commit/9eac0a122f28a7a4fa76cbfdda21d9a3571d7abb))


## v0.130.0 (2023-12-16)

### Bug Fixes

- Ensure IPv6 scoped address construction uses the string cache
  ([#1336](https://github.com/python-zeroconf/python-zeroconf/pull/1336),
  [`f78a196`](https://github.com/python-zeroconf/python-zeroconf/commit/f78a196db632c4fe017a34f1af8a58903c15a575))

- Ensure question history suppresses duplicates
  ([#1338](https://github.com/python-zeroconf/python-zeroconf/pull/1338),
  [`6f23656`](https://github.com/python-zeroconf/python-zeroconf/commit/6f23656576daa04e3de44e100f3ddd60ee4c560d))

- Microsecond precision loss in the query handler
  ([#1339](https://github.com/python-zeroconf/python-zeroconf/pull/1339),
  [`6560fad`](https://github.com/python-zeroconf/python-zeroconf/commit/6560fad584e0d392962c9a9248759f17c416620e))

- Scheduling race with the QueryScheduler
  ([#1347](https://github.com/python-zeroconf/python-zeroconf/pull/1347),
  [`cf40470`](https://github.com/python-zeroconf/python-zeroconf/commit/cf40470b89f918d3c24d7889d3536f3ffa44846c))

### Features

- Make ServiceInfo aware of question history
  ([#1348](https://github.com/python-zeroconf/python-zeroconf/pull/1348),
  [`b9aae1d`](https://github.com/python-zeroconf/python-zeroconf/commit/b9aae1de07bf1491e873bc314f8a1d7996127ad3))

- Significantly improve efficiency of the ServiceBrowser scheduler
  ([#1335](https://github.com/python-zeroconf/python-zeroconf/pull/1335),
  [`c65d869`](https://github.com/python-zeroconf/python-zeroconf/commit/c65d869aec731b803484871e9d242a984f9f5848))

- Small performance improvement constructing outgoing questions
  ([#1340](https://github.com/python-zeroconf/python-zeroconf/pull/1340),
  [`157185f`](https://github.com/python-zeroconf/python-zeroconf/commit/157185f28bf1e83e6811e2a5cd1fa9b38966f780))

- Small performance improvement for converting time
  ([#1342](https://github.com/python-zeroconf/python-zeroconf/pull/1342),
  [`73d3ab9`](https://github.com/python-zeroconf/python-zeroconf/commit/73d3ab90dd3b59caab771235dd6dbedf05bfe0b3))

- Small performance improvement for ServiceInfo asking questions
  ([#1341](https://github.com/python-zeroconf/python-zeroconf/pull/1341),
  [`810a309`](https://github.com/python-zeroconf/python-zeroconf/commit/810a3093c5a9411ee97740b468bd706bdf4a95de))

- Small speed up to processing incoming records
  ([#1345](https://github.com/python-zeroconf/python-zeroconf/pull/1345),
  [`7de655b`](https://github.com/python-zeroconf/python-zeroconf/commit/7de655b6f05012f20a3671e0bcdd44a1913d7b52))

- Small speed up to ServiceInfo construction
  ([#1346](https://github.com/python-zeroconf/python-zeroconf/pull/1346),
  [`b329d99`](https://github.com/python-zeroconf/python-zeroconf/commit/b329d99917bb731b4c70bf20c7c010eeb85ad9fd))


## v0.129.0 (2023-12-13)

### Features

- Add decoded_properties method to ServiceInfo
  ([#1332](https://github.com/python-zeroconf/python-zeroconf/pull/1332),
  [`9b595a1`](https://github.com/python-zeroconf/python-zeroconf/commit/9b595a1dcacf109c699953219d70fe36296c7318))

- Cache is_unspecified for zeroconf ip address objects
  ([#1331](https://github.com/python-zeroconf/python-zeroconf/pull/1331),
  [`a1c84dc`](https://github.com/python-zeroconf/python-zeroconf/commit/a1c84dc6adeebd155faec1a647c0f70d70de2945))

- Ensure ServiceInfo.properties always returns bytes
  ([#1333](https://github.com/python-zeroconf/python-zeroconf/pull/1333),
  [`d29553a`](https://github.com/python-zeroconf/python-zeroconf/commit/d29553ab7de6b7af70769ddb804fe2aaf492f320))


## v0.128.5 (2023-12-13)

### Bug Fixes

- Performance regression with ServiceInfo IPv6Addresses
  ([#1330](https://github.com/python-zeroconf/python-zeroconf/pull/1330),
  [`e2f9f81`](https://github.com/python-zeroconf/python-zeroconf/commit/e2f9f81dbc54c3dd527eeb3298897d63f99d33f4))


## v0.128.4 (2023-12-10)

### Bug Fixes

- Re-expose ServiceInfo._set_properties for backwards compat
  ([#1327](https://github.com/python-zeroconf/python-zeroconf/pull/1327),
  [`39c4005`](https://github.com/python-zeroconf/python-zeroconf/commit/39c40051d7a63bdc63a3e2dfa20bd944fee4e761))


## v0.128.3 (2023-12-10)

### Bug Fixes

- Correct nsec record writing
  ([#1326](https://github.com/python-zeroconf/python-zeroconf/pull/1326),
  [`cd7a16a`](https://github.com/python-zeroconf/python-zeroconf/commit/cd7a16a32c37b2f7a2e90d3c749525a5393bad57))


## v0.128.2 (2023-12-10)

### Bug Fixes

- Match cython version for dev deps to build deps
  ([#1325](https://github.com/python-zeroconf/python-zeroconf/pull/1325),
  [`a0dac46`](https://github.com/python-zeroconf/python-zeroconf/commit/a0dac46c01202b3d5a0823ac1928fc1d75332522))

- Timestamps missing double precision
  ([#1324](https://github.com/python-zeroconf/python-zeroconf/pull/1324),
  [`ecea4e4`](https://github.com/python-zeroconf/python-zeroconf/commit/ecea4e4217892ca8cf763074ac3e5d1b898acd21))


## v0.128.1 (2023-12-10)

### Bug Fixes

- Correct handling of IPv6 addresses with scope_id in ServiceInfo
  ([#1322](https://github.com/python-zeroconf/python-zeroconf/pull/1322),
  [`1682991`](https://github.com/python-zeroconf/python-zeroconf/commit/1682991b985b1f7b2bf0cff1a7eb7793070e7cb1))


## v0.128.0 (2023-12-02)

### Features

- Speed up unpacking TXT record data in ServiceInfo
  ([#1318](https://github.com/python-zeroconf/python-zeroconf/pull/1318),
  [`a200842`](https://github.com/python-zeroconf/python-zeroconf/commit/a20084281e66bdb9c37183a5eb992435f5b866ac))


## v0.127.0 (2023-11-15)

### Features

- Small speed up to processing incoming dns records
  ([#1315](https://github.com/python-zeroconf/python-zeroconf/pull/1315),
  [`bfe4c24`](https://github.com/python-zeroconf/python-zeroconf/commit/bfe4c24881a7259713425df5ab00ffe487518841))

- Small speed up to writing outgoing packets
  ([#1316](https://github.com/python-zeroconf/python-zeroconf/pull/1316),
  [`cd28476`](https://github.com/python-zeroconf/python-zeroconf/commit/cd28476f6b0a6c2c733273fb24ddaac6c7bbdf65))

- Speed up incoming packet reader
  ([#1314](https://github.com/python-zeroconf/python-zeroconf/pull/1314),
  [`0d60b61`](https://github.com/python-zeroconf/python-zeroconf/commit/0d60b61538a5d4b6f44b2369333b6e916a0a55b4))


## v0.126.0 (2023-11-13)

### Features

- Speed up outgoing packet writer
  ([#1313](https://github.com/python-zeroconf/python-zeroconf/pull/1313),
  [`55cf4cc`](https://github.com/python-zeroconf/python-zeroconf/commit/55cf4ccdff886a136db4e2133d3e6cdd001a8bd6))

- Speed up writing name compression for outgoing packets
  ([#1312](https://github.com/python-zeroconf/python-zeroconf/pull/1312),
  [`9caeabb`](https://github.com/python-zeroconf/python-zeroconf/commit/9caeabb6d4659a25ea1251c1ee7bb824e05f3d8b))


## v0.125.0 (2023-11-12)

### Features

- Speed up service browser queries when browsing many types
  ([#1311](https://github.com/python-zeroconf/python-zeroconf/pull/1311),
  [`d192d33`](https://github.com/python-zeroconf/python-zeroconf/commit/d192d33b1f05aa95a89965e86210aec086673a17))


## v0.124.0 (2023-11-12)

### Features

- Avoid decoding known answers if we have no answers to give
  ([#1308](https://github.com/python-zeroconf/python-zeroconf/pull/1308),
  [`605dc9c`](https://github.com/python-zeroconf/python-zeroconf/commit/605dc9ccd843a535802031f051b3d93310186ad1))

- Small speed up to process incoming packets
  ([#1309](https://github.com/python-zeroconf/python-zeroconf/pull/1309),
  [`56ef908`](https://github.com/python-zeroconf/python-zeroconf/commit/56ef90865189c01d2207abcc5e2efe3a7a022fa1))


## v0.123.0 (2023-11-12)

### Features

- Speed up instances only used to lookup answers
  ([#1307](https://github.com/python-zeroconf/python-zeroconf/pull/1307),
  [`0701b8a`](https://github.com/python-zeroconf/python-zeroconf/commit/0701b8ab6009891cbaddaa1d17116d31fd1b2f78))


## v0.122.3 (2023-11-09)

### Bug Fixes

- Do not build musllinux aarch64 wheels to reduce release time
  ([#1306](https://github.com/python-zeroconf/python-zeroconf/pull/1306),
  [`79aafb0`](https://github.com/python-zeroconf/python-zeroconf/commit/79aafb0acf7ca6b17976be7ede748008deada27b))


## v0.122.2 (2023-11-09)

### Bug Fixes

- Do not build aarch64 wheels for PyPy
  ([#1305](https://github.com/python-zeroconf/python-zeroconf/pull/1305),
  [`7e884db`](https://github.com/python-zeroconf/python-zeroconf/commit/7e884db4d958459e64257aba860dba2450db0687))


## v0.122.1 (2023-11-09)

### Bug Fixes

- Skip wheel builds for eol python and older python with aarch64
  ([#1304](https://github.com/python-zeroconf/python-zeroconf/pull/1304),
  [`6c8f5a5`](https://github.com/python-zeroconf/python-zeroconf/commit/6c8f5a5dec2072aa6a8f889c5d8a4623ab392234))


## v0.122.0 (2023-11-08)

### Features

- Build aarch64 wheels ([#1302](https://github.com/python-zeroconf/python-zeroconf/pull/1302),
  [`4fe58e2`](https://github.com/python-zeroconf/python-zeroconf/commit/4fe58e2edc6da64a8ece0e2b16ec9ebfc5b3cd83))


## v0.121.0 (2023-11-08)

### Features

- Speed up record updates ([#1301](https://github.com/python-zeroconf/python-zeroconf/pull/1301),
  [`d2af6a0`](https://github.com/python-zeroconf/python-zeroconf/commit/d2af6a0978f5abe4f8bb70d3e29d9836d0fd77c4))


## v0.120.0 (2023-11-05)

### Features

- Speed up decoding labels from incoming data
  ([#1291](https://github.com/python-zeroconf/python-zeroconf/pull/1291),
  [`c37ead4`](https://github.com/python-zeroconf/python-zeroconf/commit/c37ead4d7000607e81706a97b4cdffd80cf8cf99))

- Speed up incoming packet processing with a memory view
  ([#1290](https://github.com/python-zeroconf/python-zeroconf/pull/1290),
  [`f1f0a25`](https://github.com/python-zeroconf/python-zeroconf/commit/f1f0a2504afd4d29bc6b7cf715cd3cb81b9049f7))

- Speed up ServiceBrowsers with a pxd for the signal interface
  ([#1289](https://github.com/python-zeroconf/python-zeroconf/pull/1289),
  [`8a17f20`](https://github.com/python-zeroconf/python-zeroconf/commit/8a17f2053a89db4beca9e8c1de4640faf27726b4))


## v0.119.0 (2023-10-18)

### Features

- Update cibuildwheel to build wheels on latest cython final release
  ([#1285](https://github.com/python-zeroconf/python-zeroconf/pull/1285),
  [`e8c9083`](https://github.com/python-zeroconf/python-zeroconf/commit/e8c9083bb118764a85b12fac9055152a2f62a212))


## v0.118.1 (2023-10-18)

### Bug Fixes

- Reduce size of wheels by excluding generated .c files
  ([#1284](https://github.com/python-zeroconf/python-zeroconf/pull/1284),
  [`b6afa4b`](https://github.com/python-zeroconf/python-zeroconf/commit/b6afa4b2775a1fdb090145eccdc5711c98e7147a))


## v0.118.0 (2023-10-14)

### Features

- Small improvements to ServiceBrowser performance
  ([#1283](https://github.com/python-zeroconf/python-zeroconf/pull/1283),
  [`0fc031b`](https://github.com/python-zeroconf/python-zeroconf/commit/0fc031b1e7bf1766d5a1d39d70d300b86e36715e))


## v0.117.0 (2023-10-14)

### Features

- Small cleanups to incoming data handlers
  ([#1282](https://github.com/python-zeroconf/python-zeroconf/pull/1282),
  [`4f4bd9f`](https://github.com/python-zeroconf/python-zeroconf/commit/4f4bd9ff7c1e575046e5ea213d9b8c91ac7a24a9))


## v0.116.0 (2023-10-13)

### Features

- Reduce type checking overhead at run time
  ([#1281](https://github.com/python-zeroconf/python-zeroconf/pull/1281),
  [`8f30099`](https://github.com/python-zeroconf/python-zeroconf/commit/8f300996e5bd4316b2237f0502791dd0d6a855fe))


## v0.115.2 (2023-10-05)

### Bug Fixes

- Ensure ServiceInfo cache is cleared when adding to the registry
  ([#1279](https://github.com/python-zeroconf/python-zeroconf/pull/1279),
  [`2060eb2`](https://github.com/python-zeroconf/python-zeroconf/commit/2060eb2cc43489c34bea08924c3f40b875d5a498))

* There were production use cases that mutated the service info and re-registered it that need to be
  accounted for


## v0.115.1 (2023-10-01)

### Bug Fixes

- Add missing python definition for addresses_by_version
  ([#1278](https://github.com/python-zeroconf/python-zeroconf/pull/1278),
  [`52ee02b`](https://github.com/python-zeroconf/python-zeroconf/commit/52ee02b16860e344c402124f4b2e2869536ec839))


## v0.115.0 (2023-09-26)

### Features

- Speed up outgoing multicast queue
  ([#1277](https://github.com/python-zeroconf/python-zeroconf/pull/1277),
  [`a13fd49`](https://github.com/python-zeroconf/python-zeroconf/commit/a13fd49d77474fd5858de809e48cbab1ccf89173))


## v0.114.0 (2023-09-25)

### Features

- Speed up responding to queries
  ([#1275](https://github.com/python-zeroconf/python-zeroconf/pull/1275),
  [`3c6b18c`](https://github.com/python-zeroconf/python-zeroconf/commit/3c6b18cdf4c94773ad6f4497df98feb337939ee9))


## v0.113.0 (2023-09-24)

### Features

- Improve performance of loading records from cache in ServiceInfo
  ([#1274](https://github.com/python-zeroconf/python-zeroconf/pull/1274),
  [`6257d49`](https://github.com/python-zeroconf/python-zeroconf/commit/6257d49952e02107f800f4ad4894716508edfcda))


## v0.112.0 (2023-09-14)

### Features

- Improve AsyncServiceBrowser performance
  ([#1273](https://github.com/python-zeroconf/python-zeroconf/pull/1273),
  [`0c88ecf`](https://github.com/python-zeroconf/python-zeroconf/commit/0c88ecf5ef6b9b256f991e7a630048de640999a6))


## v0.111.0 (2023-09-14)

### Features

- Speed up question and answer internals
  ([#1272](https://github.com/python-zeroconf/python-zeroconf/pull/1272),
  [`d24722b`](https://github.com/python-zeroconf/python-zeroconf/commit/d24722bfa4201d48ab482d35b0ef004f070ada80))


## v0.110.0 (2023-09-14)

### Features

- Small speed ups to ServiceBrowser
  ([#1271](https://github.com/python-zeroconf/python-zeroconf/pull/1271),
  [`22c433d`](https://github.com/python-zeroconf/python-zeroconf/commit/22c433ddaea3049ac49933325ba938fd87a529c0))


## v0.109.0 (2023-09-14)

### Features

- Speed up ServiceBrowsers with a cython pxd
  ([#1270](https://github.com/python-zeroconf/python-zeroconf/pull/1270),
  [`4837876`](https://github.com/python-zeroconf/python-zeroconf/commit/48378769c3887b5746ca00de30067a4c0851765c))


## v0.108.0 (2023-09-11)

### Features

- Improve performance of constructing outgoing queries
  ([#1267](https://github.com/python-zeroconf/python-zeroconf/pull/1267),
  [`00c439a`](https://github.com/python-zeroconf/python-zeroconf/commit/00c439a6400b7850ef9fdd75bc8d82d4e64b1da0))


## v0.107.0 (2023-09-11)

### Features

- Speed up responding to queries
  ([#1266](https://github.com/python-zeroconf/python-zeroconf/pull/1266),
  [`24a0a00`](https://github.com/python-zeroconf/python-zeroconf/commit/24a0a00b3e457979e279a2eeadc8fad2ab09e125))


## v0.106.0 (2023-09-11)

### Features

- Speed up answering questions
  ([#1265](https://github.com/python-zeroconf/python-zeroconf/pull/1265),
  [`37bfaf2`](https://github.com/python-zeroconf/python-zeroconf/commit/37bfaf2f630358e8c68652f3b3120931a6f94910))


## v0.105.0 (2023-09-10)

### Features

- Speed up ServiceInfo with a cython pxd
  ([#1264](https://github.com/python-zeroconf/python-zeroconf/pull/1264),
  [`7ca690a`](https://github.com/python-zeroconf/python-zeroconf/commit/7ca690ac3fa75e7474d3412944bbd5056cb313dd))


## v0.104.0 (2023-09-10)

### Features

- Speed up generating answers
  ([#1262](https://github.com/python-zeroconf/python-zeroconf/pull/1262),
  [`50a8f06`](https://github.com/python-zeroconf/python-zeroconf/commit/50a8f066b6ab90bc9e3300f81cf9332550b720df))


## v0.103.0 (2023-09-09)

### Features

- Avoid calling get_running_loop when resolving ServiceInfo
  ([#1261](https://github.com/python-zeroconf/python-zeroconf/pull/1261),
  [`33a2714`](https://github.com/python-zeroconf/python-zeroconf/commit/33a2714cadff96edf016b869cc63b0661d16ef2c))


## v0.102.0 (2023-09-07)

### Features

- Significantly speed up writing outgoing dns records
  ([#1260](https://github.com/python-zeroconf/python-zeroconf/pull/1260),
  [`bf2f366`](https://github.com/python-zeroconf/python-zeroconf/commit/bf2f3660a1f341e50ab0ae586dfbacbc5ddcc077))


## v0.101.0 (2023-09-07)

### Features

- Speed up writing outgoing dns records
  ([#1259](https://github.com/python-zeroconf/python-zeroconf/pull/1259),
  [`248655f`](https://github.com/python-zeroconf/python-zeroconf/commit/248655f0276223b089373c70ec13a0385dfaa4d6))


## v0.100.0 (2023-09-07)

### Features

- Small speed up to writing outgoing dns records
  ([#1258](https://github.com/python-zeroconf/python-zeroconf/pull/1258),
  [`1ed6bd2`](https://github.com/python-zeroconf/python-zeroconf/commit/1ed6bd2ec4db0612b71384f923ffff1efd3ce878))


## v0.99.0 (2023-09-06)

### Features

- Reduce IP Address parsing overhead in ServiceInfo
  ([#1257](https://github.com/python-zeroconf/python-zeroconf/pull/1257),
  [`83d0b7f`](https://github.com/python-zeroconf/python-zeroconf/commit/83d0b7fda2eb09c9c6e18b85f329d1ddc701e3fb))


## v0.98.0 (2023-09-06)

### Features

- Speed up decoding incoming packets
  ([#1256](https://github.com/python-zeroconf/python-zeroconf/pull/1256),
  [`ac081cf`](https://github.com/python-zeroconf/python-zeroconf/commit/ac081cf00addde1ceea2c076f73905fdb293de3a))


## v0.97.0 (2023-09-03)

### Features

- Speed up answering queries ([#1255](https://github.com/python-zeroconf/python-zeroconf/pull/1255),
  [`2d3aed3`](https://github.com/python-zeroconf/python-zeroconf/commit/2d3aed36e24c73013fcf4acc90803fc1737d0917))


## v0.96.0 (2023-09-03)

### Features

- Optimize DNSCache.get_by_details
  ([#1254](https://github.com/python-zeroconf/python-zeroconf/pull/1254),
  [`ce59787`](https://github.com/python-zeroconf/python-zeroconf/commit/ce59787a170781ffdaa22425018d288b395ac081))

* feat: optimize DNSCache.get_by_details

This is one of the most called functions since ServiceInfo.load_from_cache calls it

* fix: make get_all_by_details thread-safe

* fix: remove unneeded key checks


## v0.95.0 (2023-09-03)

### Features

- Speed up adding and removing RecordUpdateListeners
  ([#1253](https://github.com/python-zeroconf/python-zeroconf/pull/1253),
  [`22e4a29`](https://github.com/python-zeroconf/python-zeroconf/commit/22e4a296d440b3038c0ff5ed6fc8878304ec4937))


## v0.94.0 (2023-09-03)

### Features

- Optimize cache implementation
  ([#1252](https://github.com/python-zeroconf/python-zeroconf/pull/1252),
  [`8d3ec79`](https://github.com/python-zeroconf/python-zeroconf/commit/8d3ec792277aaf7ef790318b5b35ab00839ca3b3))


## v0.93.1 (2023-09-03)

### Bug Fixes

- No change re-release due to unrecoverable failed CI run
  ([#1251](https://github.com/python-zeroconf/python-zeroconf/pull/1251),
  [`730921b`](https://github.com/python-zeroconf/python-zeroconf/commit/730921b155dfb9c62251c8c643b1302e807aff3b))


## v0.93.0 (2023-09-02)

### Features

- Reduce overhead to answer questions
  ([#1250](https://github.com/python-zeroconf/python-zeroconf/pull/1250),
  [`7cb8da0`](https://github.com/python-zeroconf/python-zeroconf/commit/7cb8da0c6c5c944588009fe36012c1197c422668))


## v0.92.0 (2023-09-02)

### Features

- Cache construction of records used to answer queries from the service registry
  ([#1243](https://github.com/python-zeroconf/python-zeroconf/pull/1243),
  [`0890f62`](https://github.com/python-zeroconf/python-zeroconf/commit/0890f628dbbd577fb77d3e6f2e267052b2b2b515))


## v0.91.1 (2023-09-02)

### Bug Fixes

- Remove useless calls in ServiceInfo
  ([#1248](https://github.com/python-zeroconf/python-zeroconf/pull/1248),
  [`4e40fae`](https://github.com/python-zeroconf/python-zeroconf/commit/4e40fae20bf50b4608e28fad4a360c4ed48ac86b))


## v0.91.0 (2023-09-02)

### Features

- Reduce overhead to process incoming updates by avoiding the handle_response shim
  ([#1247](https://github.com/python-zeroconf/python-zeroconf/pull/1247),
  [`5e31f0a`](https://github.com/python-zeroconf/python-zeroconf/commit/5e31f0afe4c341fbdbbbe50348a829ea553cbda0))


## v0.90.0 (2023-09-02)

### Features

- Avoid python float conversion in listener hot path
  ([#1245](https://github.com/python-zeroconf/python-zeroconf/pull/1245),
  [`816ad4d`](https://github.com/python-zeroconf/python-zeroconf/commit/816ad4dceb3859bad4bb136bdb1d1ee2daa0bf5a))

### Refactoring

- Reduce duplicate code in engine.py
  ([#1246](https://github.com/python-zeroconf/python-zeroconf/pull/1246),
  [`36ae505`](https://github.com/python-zeroconf/python-zeroconf/commit/36ae505dc9f95b59fdfb632960845a45ba8575b8))


## v0.89.0 (2023-09-02)

### Features

- Reduce overhead to process incoming questions
  ([#1244](https://github.com/python-zeroconf/python-zeroconf/pull/1244),
  [`18b65d1`](https://github.com/python-zeroconf/python-zeroconf/commit/18b65d1c75622869b0c29258215d3db3ae520d6c))


## v0.88.0 (2023-08-29)

### Features

- Speed up RecordManager with additional cython defs
  ([#1242](https://github.com/python-zeroconf/python-zeroconf/pull/1242),
  [`5a76fc5`](https://github.com/python-zeroconf/python-zeroconf/commit/5a76fc5ff74f2941ffbf7570e45390f35e0b7e01))


## v0.87.0 (2023-08-29)

### Features

- Improve performance by adding cython pxd for RecordManager
  ([#1241](https://github.com/python-zeroconf/python-zeroconf/pull/1241),
  [`a7dad3d`](https://github.com/python-zeroconf/python-zeroconf/commit/a7dad3d9743586f352e21eea1e129c6875f9a713))


## v0.86.0 (2023-08-28)

### Features

- Build wheels for cpython 3.12
  ([#1239](https://github.com/python-zeroconf/python-zeroconf/pull/1239),
  [`58bc154`](https://github.com/python-zeroconf/python-zeroconf/commit/58bc154f55b06b4ddfc4a141592488abe76f062a))

- Use server_key when processing DNSService records
  ([#1238](https://github.com/python-zeroconf/python-zeroconf/pull/1238),
  [`cc8feb1`](https://github.com/python-zeroconf/python-zeroconf/commit/cc8feb110fefc3fb714fd482a52f16e2b620e8c4))


## v0.85.0 (2023-08-27)

### Features

- Simplify code to unpack properties
  ([#1237](https://github.com/python-zeroconf/python-zeroconf/pull/1237),
  [`68d9998`](https://github.com/python-zeroconf/python-zeroconf/commit/68d99985a0e9d2c72ff670b2e2af92271a6fe934))


## v0.84.0 (2023-08-27)

### Features

- Context managers in ServiceBrowser and AsyncServiceBrowser
  ([#1233](https://github.com/python-zeroconf/python-zeroconf/pull/1233),
  [`bd8d846`](https://github.com/python-zeroconf/python-zeroconf/commit/bd8d8467dec2a39a0b525043ea1051259100fded))

Co-authored-by: J. Nick Koston <nick@koston.org>


## v0.83.1 (2023-08-27)

### Bug Fixes

- Rebuild wheels with cython 3.0.2
  ([#1236](https://github.com/python-zeroconf/python-zeroconf/pull/1236),
  [`dd637fb`](https://github.com/python-zeroconf/python-zeroconf/commit/dd637fb2e5a87ba283750e69d116e124bef54e7c))


## v0.83.0 (2023-08-26)

### Features

- Speed up question and answer history with a cython pxd
  ([#1234](https://github.com/python-zeroconf/python-zeroconf/pull/1234),
  [`703ecb2`](https://github.com/python-zeroconf/python-zeroconf/commit/703ecb2901b2150fb72fac3deed61d7302561298))


## v0.82.1 (2023-08-22)

### Bug Fixes

- Build failures with older cython 0.29 series
  ([#1232](https://github.com/python-zeroconf/python-zeroconf/pull/1232),
  [`30c3ad9`](https://github.com/python-zeroconf/python-zeroconf/commit/30c3ad9d1bc6b589e1ca6675fea21907ebcd1ced))


## v0.82.0 (2023-08-22)

### Features

- Optimize processing of records in RecordUpdateListener subclasses
  ([#1231](https://github.com/python-zeroconf/python-zeroconf/pull/1231),
  [`3e89294`](https://github.com/python-zeroconf/python-zeroconf/commit/3e89294ea0ecee1122e1c1ffdc78925add8ca40e))


## v0.81.0 (2023-08-22)

### Features

- Optimizing sending answers to questions
  ([#1227](https://github.com/python-zeroconf/python-zeroconf/pull/1227),
  [`cd7b56b`](https://github.com/python-zeroconf/python-zeroconf/commit/cd7b56b2aa0c8ee429da430e9a36abd515512011))

- Speed up the service registry with a cython pxd
  ([#1226](https://github.com/python-zeroconf/python-zeroconf/pull/1226),
  [`47d3c7a`](https://github.com/python-zeroconf/python-zeroconf/commit/47d3c7ad4bc5f2247631c3ad5e6b6156d45a0a4e))


## v0.80.0 (2023-08-15)

### Features

- Optimize unpacking properties in ServiceInfo
  ([#1225](https://github.com/python-zeroconf/python-zeroconf/pull/1225),
  [`1492e41`](https://github.com/python-zeroconf/python-zeroconf/commit/1492e41b3d5cba5598cc9dd6bd2bc7d238f13555))


## v0.79.0 (2023-08-14)

### Features

- Refactor notify implementation to reduce overhead of adding and removing listeners
  ([#1224](https://github.com/python-zeroconf/python-zeroconf/pull/1224),
  [`ceb92cf`](https://github.com/python-zeroconf/python-zeroconf/commit/ceb92cfe42d885dbb38cee7aaeebf685d97627a9))


## v0.78.0 (2023-08-14)

### Features

- Add cython pxd file for _listener.py to improve incoming message processing performance
  ([#1221](https://github.com/python-zeroconf/python-zeroconf/pull/1221),
  [`f459856`](https://github.com/python-zeroconf/python-zeroconf/commit/f459856a0a61b8afa8a541926d7e15d51f8e4aea))


## v0.77.0 (2023-08-14)

### Features

- Cythonize _listener.py to improve incoming message processing performance
  ([#1220](https://github.com/python-zeroconf/python-zeroconf/pull/1220),
  [`9efde8c`](https://github.com/python-zeroconf/python-zeroconf/commit/9efde8c8c1ed14c5d3c162f185b49212fcfcb5c9))


## v0.76.0 (2023-08-14)

### Features

- Improve performance responding to queries
  ([#1217](https://github.com/python-zeroconf/python-zeroconf/pull/1217),
  [`69b33be`](https://github.com/python-zeroconf/python-zeroconf/commit/69b33be3b2f9d4a27ef5154cae94afca048efffa))


## v0.75.0 (2023-08-13)

### Features

- Expose flag to disable strict name checking in service registration
  ([#1215](https://github.com/python-zeroconf/python-zeroconf/pull/1215),
  [`5df8a57`](https://github.com/python-zeroconf/python-zeroconf/commit/5df8a57a14d59687a3c22ea8ee063e265031e278))

- Speed up processing incoming records
  ([#1216](https://github.com/python-zeroconf/python-zeroconf/pull/1216),
  [`aff625d`](https://github.com/python-zeroconf/python-zeroconf/commit/aff625dc6a5e816dad519644c4adac4f96980c04))


## v0.74.0 (2023-08-04)

### Bug Fixes

- Remove typing on reset_ttl for cython compat
  ([#1213](https://github.com/python-zeroconf/python-zeroconf/pull/1213),
  [`0094e26`](https://github.com/python-zeroconf/python-zeroconf/commit/0094e2684344c6b7edd7948924f093f1b4c19901))

### Features

- Speed up unpacking text records in ServiceInfo
  ([#1212](https://github.com/python-zeroconf/python-zeroconf/pull/1212),
  [`99a6f98`](https://github.com/python-zeroconf/python-zeroconf/commit/99a6f98e44a1287ba537eabb852b1b69923402f0))


## v0.73.0 (2023-08-03)

### Features

- Add a cache to service_type_name
  ([#1211](https://github.com/python-zeroconf/python-zeroconf/pull/1211),
  [`53a694f`](https://github.com/python-zeroconf/python-zeroconf/commit/53a694f60e675ae0560e727be6b721b401c2b68f))


## v0.72.3 (2023-08-03)

### Bug Fixes

- Revert adding typing to DNSRecord.suppressed_by
  ([#1210](https://github.com/python-zeroconf/python-zeroconf/pull/1210),
  [`3dba5ae`](https://github.com/python-zeroconf/python-zeroconf/commit/3dba5ae0c0e9473b7b20fd6fc79fa1a3b298dc5a))


## v0.72.2 (2023-08-03)

### Bug Fixes

- Revert DNSIncoming cimport in _dns.pxd
  ([#1209](https://github.com/python-zeroconf/python-zeroconf/pull/1209),
  [`5f14b6d`](https://github.com/python-zeroconf/python-zeroconf/commit/5f14b6dc687b3a0716d0ca7f61ccf1e93dfe5fa1))


## v0.72.1 (2023-08-03)

### Bug Fixes

- Race with InvalidStateError when async_request times out
  ([#1208](https://github.com/python-zeroconf/python-zeroconf/pull/1208),
  [`2233b6b`](https://github.com/python-zeroconf/python-zeroconf/commit/2233b6bc4ceeee5524d2ee88ecae8234173feb5f))


## v0.72.0 (2023-08-02)

### Features

- Speed up processing incoming records
  ([#1206](https://github.com/python-zeroconf/python-zeroconf/pull/1206),
  [`126849c`](https://github.com/python-zeroconf/python-zeroconf/commit/126849c92be8cec9253fba9faa591029d992fcc3))


## v0.71.5 (2023-08-02)

### Bug Fixes

- Improve performance of ServiceInfo.async_request
  ([#1205](https://github.com/python-zeroconf/python-zeroconf/pull/1205),
  [`8019a73`](https://github.com/python-zeroconf/python-zeroconf/commit/8019a73c952f2fc4c88d849aab970fafedb316d8))


## v0.71.4 (2023-07-24)

### Bug Fixes

- Cleanup naming from previous refactoring in ServiceInfo
  ([#1202](https://github.com/python-zeroconf/python-zeroconf/pull/1202),
  [`b272d75`](https://github.com/python-zeroconf/python-zeroconf/commit/b272d75abd982f3be1f4b20f683cac38011cc6f4))


## v0.71.3 (2023-07-23)

### Bug Fixes

- Pin python-semantic-release to fix release process
  ([#1200](https://github.com/python-zeroconf/python-zeroconf/pull/1200),
  [`c145a23`](https://github.com/python-zeroconf/python-zeroconf/commit/c145a238d768aa17c3aebe120c20a46bfbec6b99))


## v0.71.2 (2023-07-23)

### Bug Fixes

- No change re-release to fix wheel builds
  ([#1199](https://github.com/python-zeroconf/python-zeroconf/pull/1199),
  [`8c3a4c8`](https://github.com/python-zeroconf/python-zeroconf/commit/8c3a4c80c221bea7401c12e1c6a525e75b7ffea2))


## v0.71.1 (2023-07-23)

### Bug Fixes

- Add missing if TYPE_CHECKING guard to generate_service_query
  ([#1198](https://github.com/python-zeroconf/python-zeroconf/pull/1198),
  [`ac53adf`](https://github.com/python-zeroconf/python-zeroconf/commit/ac53adf7e71db14c1a0f9adbfd1d74033df36898))


## v0.71.0 (2023-07-08)

### Features

- Improve incoming data processing performance
  ([#1194](https://github.com/python-zeroconf/python-zeroconf/pull/1194),
  [`a56c776`](https://github.com/python-zeroconf/python-zeroconf/commit/a56c776008ef86f99db78f5997e45a57551be725))


## v0.70.0 (2023-07-02)

### Features

- Add support for sending to a specific `addr` and `port` with `ServiceInfo.async_request` and
  `ServiceInfo.request` ([#1192](https://github.com/python-zeroconf/python-zeroconf/pull/1192),
  [`405f547`](https://github.com/python-zeroconf/python-zeroconf/commit/405f54762d3f61e97de9c1787e837e953de31412))


## v0.69.0 (2023-06-18)

### Features

- Cython3 support ([#1190](https://github.com/python-zeroconf/python-zeroconf/pull/1190),
  [`8ae8ba1`](https://github.com/python-zeroconf/python-zeroconf/commit/8ae8ba1af324b0c8c2da3bd12c264a5c0f3dcc3d))

- Reorder incoming data handler to reduce overhead
  ([#1189](https://github.com/python-zeroconf/python-zeroconf/pull/1189),
  [`32756ff`](https://github.com/python-zeroconf/python-zeroconf/commit/32756ff113f675b7a9cf16d3c0ab840ba733e5e4))


## v0.68.1 (2023-06-18)

### Bug Fixes

- Reduce debug logging overhead by adding missing checks to datagram_received
  ([#1188](https://github.com/python-zeroconf/python-zeroconf/pull/1188),
  [`ac5c50a`](https://github.com/python-zeroconf/python-zeroconf/commit/ac5c50afc70aaa33fcd20bf02222ff4f0c596fa3))


## v0.68.0 (2023-06-17)

### Features

- Reduce overhead to handle queries and responses
  ([#1184](https://github.com/python-zeroconf/python-zeroconf/pull/1184),
  [`81126b7`](https://github.com/python-zeroconf/python-zeroconf/commit/81126b7600f94848ef8c58b70bac0c6ab993c6ae))

- adds slots to handler classes

- avoid any expression overhead and inline instead


## v0.67.0 (2023-06-17)

### Features

- Speed up answering incoming questions
  ([#1186](https://github.com/python-zeroconf/python-zeroconf/pull/1186),
  [`8f37665`](https://github.com/python-zeroconf/python-zeroconf/commit/8f376658d2a3bef0353646e6fddfda15626b73a9))


## v0.66.0 (2023-06-13)

### Features

- Optimize construction of outgoing dns records
  ([#1182](https://github.com/python-zeroconf/python-zeroconf/pull/1182),
  [`fc0341f`](https://github.com/python-zeroconf/python-zeroconf/commit/fc0341f281cdb71428c0f1cf90c12d34cbb4acae))


## v0.65.0 (2023-06-13)

### Features

- Reduce overhead to enumerate ip addresses in ServiceInfo
  ([#1181](https://github.com/python-zeroconf/python-zeroconf/pull/1181),
  [`6a85cbf`](https://github.com/python-zeroconf/python-zeroconf/commit/6a85cbf2b872cb0abd184c2dd728d9ae3eb8115c))


## v0.64.1 (2023-06-05)

### Bug Fixes

- Small internal typing cleanups
  ([#1180](https://github.com/python-zeroconf/python-zeroconf/pull/1180),
  [`f03e511`](https://github.com/python-zeroconf/python-zeroconf/commit/f03e511f7aae72c5ccd4f7514d89e168847bd7a2))


## v0.64.0 (2023-06-05)

### Bug Fixes

- Always answer QU questions when the exact same packet is received from different sources in
  sequence ([#1178](https://github.com/python-zeroconf/python-zeroconf/pull/1178),
  [`74d7ba1`](https://github.com/python-zeroconf/python-zeroconf/commit/74d7ba1aeeae56be087ee8142ee6ca1219744baa))

If the exact same packet with a QU question is asked from two different sources in a 1s window we
  end up ignoring the second one as a duplicate. We should still respond in this case because the
  client wants a unicast response and the question may not be answered by the previous packet since
  the response may not be multicast.

fix: include NSEC records in initial broadcast when registering a new service

This also revealed that we do not send NSEC records in the initial broadcast. This needed to be
  fixed in this PR as well for everything to work as expected since all the tests would fail with 2
  updates otherwise.

### Features

- Speed up processing incoming records
  ([#1179](https://github.com/python-zeroconf/python-zeroconf/pull/1179),
  [`d919316`](https://github.com/python-zeroconf/python-zeroconf/commit/d9193160b05beeca3755e19fd377ba13fe37b071))


## v0.63.0 (2023-05-25)

### Features

- Improve dns cache performance
  ([#1172](https://github.com/python-zeroconf/python-zeroconf/pull/1172),
  [`bb496a1`](https://github.com/python-zeroconf/python-zeroconf/commit/bb496a1dd5fa3562c0412cb064d14639a542592e))

- Small speed up to fetch dns addresses from ServiceInfo
  ([#1176](https://github.com/python-zeroconf/python-zeroconf/pull/1176),
  [`4deaa6e`](https://github.com/python-zeroconf/python-zeroconf/commit/4deaa6ed7c9161db55bf16ec068ab7260bbd4976))

- Speed up the service registry
  ([#1174](https://github.com/python-zeroconf/python-zeroconf/pull/1174),
  [`360ceb2`](https://github.com/python-zeroconf/python-zeroconf/commit/360ceb2548c4c4974ff798aac43a6fff9803ea0e))


## v0.62.0 (2023-05-04)

### Features

- Improve performance of ServiceBrowser outgoing query scheduler
  ([#1170](https://github.com/python-zeroconf/python-zeroconf/pull/1170),
  [`963d022`](https://github.com/python-zeroconf/python-zeroconf/commit/963d022ef82b615540fa7521d164a98a6c6f5209))


## v0.61.0 (2023-05-03)

### Features

- Speed up parsing NSEC records
  ([#1169](https://github.com/python-zeroconf/python-zeroconf/pull/1169),
  [`06fa94d`](https://github.com/python-zeroconf/python-zeroconf/commit/06fa94d87b4f0451cb475a921ce1d8e9562e0f26))


## v0.60.0 (2023-05-01)

### Features

- Speed up processing incoming data
  ([#1167](https://github.com/python-zeroconf/python-zeroconf/pull/1167),
  [`fbaaf7b`](https://github.com/python-zeroconf/python-zeroconf/commit/fbaaf7bb6ff985bdabb85feb6cba144f12d4f1d6))


## v0.59.0 (2023-05-01)

### Features

- Speed up decoding dns questions when processing incoming data
  ([#1168](https://github.com/python-zeroconf/python-zeroconf/pull/1168),
  [`f927190`](https://github.com/python-zeroconf/python-zeroconf/commit/f927190cb24f70fd7c825c6e12151fcc0daf3973))


## v0.58.2 (2023-04-26)

### Bug Fixes

- Re-release to rebuild failed wheels
  ([#1165](https://github.com/python-zeroconf/python-zeroconf/pull/1165),
  [`4986271`](https://github.com/python-zeroconf/python-zeroconf/commit/498627166a4976f1d9d8cd1f3654b0d50272d266))


## v0.58.1 (2023-04-26)

### Bug Fixes

- Reduce cast calls in service browser
  ([#1164](https://github.com/python-zeroconf/python-zeroconf/pull/1164),
  [`c0d65ae`](https://github.com/python-zeroconf/python-zeroconf/commit/c0d65aeae7037a18ed1149336f5e7bdb8b2dd8cf))


## v0.58.0 (2023-04-23)

### Features

- Speed up incoming parser ([#1163](https://github.com/python-zeroconf/python-zeroconf/pull/1163),
  [`4626399`](https://github.com/python-zeroconf/python-zeroconf/commit/46263999c0c7ea5176885f1eadd2c8498834b70e))


## v0.57.0 (2023-04-23)

### Features

- Speed up incoming data parser
  ([#1161](https://github.com/python-zeroconf/python-zeroconf/pull/1161),
  [`cb4c3b2`](https://github.com/python-zeroconf/python-zeroconf/commit/cb4c3b2b80ca3b88b8de6e87062a45e03e8805a6))


## v0.56.0 (2023-04-07)

### Features

- Reduce denial of service protection overhead
  ([#1157](https://github.com/python-zeroconf/python-zeroconf/pull/1157),
  [`2c2f26a`](https://github.com/python-zeroconf/python-zeroconf/commit/2c2f26a87d0aac81a77205b06bc9ba499caa2321))


## v0.55.0 (2023-04-07)

### Features

- Improve performance of processing incoming records
  ([#1155](https://github.com/python-zeroconf/python-zeroconf/pull/1155),
  [`b65e279`](https://github.com/python-zeroconf/python-zeroconf/commit/b65e2792751c44e0fafe9ad3a55dadc5d8ee9d46))


## v0.54.0 (2023-04-03)

### Features

- Avoid waking async_request when record updates are not relevant
  ([#1153](https://github.com/python-zeroconf/python-zeroconf/pull/1153),
  [`a3f970c`](https://github.com/python-zeroconf/python-zeroconf/commit/a3f970c7f66067cf2c302c49ed6ad8286f19b679))


## v0.53.1 (2023-04-03)

### Bug Fixes

- Addresses incorrect after server name change
  ([#1154](https://github.com/python-zeroconf/python-zeroconf/pull/1154),
  [`41ea06a`](https://github.com/python-zeroconf/python-zeroconf/commit/41ea06a0192c0d186e678009285759eb37d880d5))


## v0.53.0 (2023-04-02)

### Bug Fixes

- Make parsed_scoped_addresses return addresses in the same order as all other methods
  ([#1150](https://github.com/python-zeroconf/python-zeroconf/pull/1150),
  [`9b6adcf`](https://github.com/python-zeroconf/python-zeroconf/commit/9b6adcf5c04a469632ee866c32f5898c5cbf810a))

### Features

- Improve ServiceBrowser performance by removing OrderedDict
  ([#1148](https://github.com/python-zeroconf/python-zeroconf/pull/1148),
  [`9a16be5`](https://github.com/python-zeroconf/python-zeroconf/commit/9a16be56a9f69a5d0f7cde13dc1337b6d93c1433))


## v0.52.0 (2023-04-02)

### Features

- Add ip_addresses_by_version to ServiceInfo
  ([#1145](https://github.com/python-zeroconf/python-zeroconf/pull/1145),
  [`524494e`](https://github.com/python-zeroconf/python-zeroconf/commit/524494edd49bd049726b19ae8ac8f6eea69a3943))

- Include tests and docs in sdist archives
  ([#1142](https://github.com/python-zeroconf/python-zeroconf/pull/1142),
  [`da10a3b`](https://github.com/python-zeroconf/python-zeroconf/commit/da10a3b2827cee0719d3bb9152ae897f061c6e2e))

feat: Include tests and docs in sdist archives

Include documentation and test files in source distributions, in order to make them more useful for
  packagers (Linux distributions, Conda). Testing is an important part of packaging process, and at
  least Gentoo users have requested offline documentation for Python packages. Furthermore, the
  COPYING file was missing from sdist, even though it was referenced in README.

- Small cleanups to cache cleanup interval
  ([#1146](https://github.com/python-zeroconf/python-zeroconf/pull/1146),
  [`b434b60`](https://github.com/python-zeroconf/python-zeroconf/commit/b434b60f14ebe8f114b7b19bb4f54081c8ae0173))

- Speed up matching types in the ServiceBrowser
  ([#1144](https://github.com/python-zeroconf/python-zeroconf/pull/1144),
  [`68871c3`](https://github.com/python-zeroconf/python-zeroconf/commit/68871c3b5569e41740a66b7d3d7fa5cc41514ea5))

- Speed up processing records in the ServiceBrowser
  ([#1143](https://github.com/python-zeroconf/python-zeroconf/pull/1143),
  [`6a327d0`](https://github.com/python-zeroconf/python-zeroconf/commit/6a327d00ffb81de55b7c5b599893c789996680c1))


## v0.51.0 (2023-04-01)

### Features

- Improve performance of constructing ServiceInfo
  ([#1141](https://github.com/python-zeroconf/python-zeroconf/pull/1141),
  [`36d5b45`](https://github.com/python-zeroconf/python-zeroconf/commit/36d5b45a4ece1dca902e9c3c79b5a63b8d9ae41f))


## v0.50.0 (2023-04-01)

### Features

- Small speed up to handler dispatch
  ([#1140](https://github.com/python-zeroconf/python-zeroconf/pull/1140),
  [`5bd1b6e`](https://github.com/python-zeroconf/python-zeroconf/commit/5bd1b6e7b4dd796069461c737ded956305096307))


## v0.49.0 (2023-04-01)

### Features

- Speed up processing incoming records
  ([#1139](https://github.com/python-zeroconf/python-zeroconf/pull/1139),
  [`7246a34`](https://github.com/python-zeroconf/python-zeroconf/commit/7246a344b6c0543871b40715c95c9435db4c7f81))


## v0.48.0 (2023-04-01)

### Features

- Reduce overhead to send responses
  ([#1135](https://github.com/python-zeroconf/python-zeroconf/pull/1135),
  [`c4077dd`](https://github.com/python-zeroconf/python-zeroconf/commit/c4077dde6dfde9e2598eb63daa03c36063a3e7b0))


## v0.47.4 (2023-03-20)

### Bug Fixes

- Correct duplicate record entries in windows wheels by updating poetry-core
  ([#1134](https://github.com/python-zeroconf/python-zeroconf/pull/1134),
  [`a43055d`](https://github.com/python-zeroconf/python-zeroconf/commit/a43055d3fa258cd762c3e9394b01f8bdcb24f97e))


## v0.47.3 (2023-02-14)

### Bug Fixes

- Hold a strong reference to the query sender start task
  ([#1128](https://github.com/python-zeroconf/python-zeroconf/pull/1128),
  [`808c3b2`](https://github.com/python-zeroconf/python-zeroconf/commit/808c3b2194a7f499a469a9893102d328ccee83db))


## v0.47.2 (2023-02-14)

### Bug Fixes

- Missing c extensions with newer poetry
  ([#1129](https://github.com/python-zeroconf/python-zeroconf/pull/1129),
  [`44d7fc6`](https://github.com/python-zeroconf/python-zeroconf/commit/44d7fc6483485102f60c91d591d0d697872f8865))


## v0.47.1 (2022-12-24)

### Bug Fixes

- The equality checks for DNSPointer and DNSService should be case insensitive
  ([#1122](https://github.com/python-zeroconf/python-zeroconf/pull/1122),
  [`48ae77f`](https://github.com/python-zeroconf/python-zeroconf/commit/48ae77f026a96e2ca475b0ff80cb6d22207ce52f))


## v0.47.0 (2022-12-22)

### Features

- Optimize equality checks for DNS records
  ([#1120](https://github.com/python-zeroconf/python-zeroconf/pull/1120),
  [`3a25ff7`](https://github.com/python-zeroconf/python-zeroconf/commit/3a25ff74bea83cd7d50888ce1ebfd7650d704bfa))


## v0.46.0 (2022-12-21)

### Features

- Optimize the dns cache ([#1119](https://github.com/python-zeroconf/python-zeroconf/pull/1119),
  [`e80fcef`](https://github.com/python-zeroconf/python-zeroconf/commit/e80fcef967024f8e846e44b464a82a25f5550edf))


## v0.45.0 (2022-12-20)

### Features

- Optimize construction of outgoing packets
  ([#1118](https://github.com/python-zeroconf/python-zeroconf/pull/1118),
  [`81e186d`](https://github.com/python-zeroconf/python-zeroconf/commit/81e186d365c018381f9b486a4dbe4e2e4b8bacbf))


## v0.44.0 (2022-12-18)

### Features

- Optimize dns objects by adding pxd files
  ([#1113](https://github.com/python-zeroconf/python-zeroconf/pull/1113),
  [`919d4d8`](https://github.com/python-zeroconf/python-zeroconf/commit/919d4d875747b4fa68e25bccd5aae7f304d8a36d))


## v0.43.0 (2022-12-18)

### Features

- Optimize incoming parser by reducing call stack
  ([#1116](https://github.com/python-zeroconf/python-zeroconf/pull/1116),
  [`11f3f0e`](https://github.com/python-zeroconf/python-zeroconf/commit/11f3f0e699e00c1ee3d6d8ab5e30f62525510589))


## v0.42.0 (2022-12-18)

### Features

- Optimize incoming parser by using unpack_from
  ([#1115](https://github.com/python-zeroconf/python-zeroconf/pull/1115),
  [`a7d50ba`](https://github.com/python-zeroconf/python-zeroconf/commit/a7d50baab362eadd2d292df08a39de6836b41ea7))


## v0.41.0 (2022-12-18)

### Features

- Optimize incoming parser by adding pxd files
  ([#1111](https://github.com/python-zeroconf/python-zeroconf/pull/1111),
  [`26efeb0`](https://github.com/python-zeroconf/python-zeroconf/commit/26efeb09783050266242542228f34eb4dd83e30c))


## v0.40.1 (2022-12-18)

### Bug Fixes

- Fix project name in pyproject.toml
  ([#1112](https://github.com/python-zeroconf/python-zeroconf/pull/1112),
  [`a330f62`](https://github.com/python-zeroconf/python-zeroconf/commit/a330f62040475257c4a983044e1675aeb95e030a))


## v0.40.0 (2022-12-17)

### Features

- Drop async_timeout requirement for python 3.11+
  ([#1107](https://github.com/python-zeroconf/python-zeroconf/pull/1107),
  [`1f4224e`](https://github.com/python-zeroconf/python-zeroconf/commit/1f4224ef122299235013cb81b501f8ff9a30dea1))


## v0.39.5 (2022-12-17)


## v0.39.4 (2022-10-31)


## v0.39.3 (2022-10-26)


## v0.39.2 (2022-10-20)


## v0.39.1 (2022-09-05)


## v0.39.0 (2022-08-05)


## v0.38.7 (2022-06-14)


## v0.38.6 (2022-05-06)


## v0.38.5 (2022-05-01)


## v0.38.4 (2022-02-28)


## v0.38.3 (2022-01-31)


## v0.38.2 (2022-01-31)


## v0.38.1 (2021-12-23)


## v0.38.0 (2021-12-23)


## v0.37.0 (2021-11-18)


## v0.36.13 (2021-11-13)


## v0.36.12 (2021-11-05)


## v0.36.11 (2021-10-30)


## v0.36.10 (2021-10-30)


## v0.36.9 (2021-10-22)


## v0.36.8 (2021-10-10)


## v0.36.7 (2021-09-22)


## v0.36.6 (2021-09-19)


## v0.36.5 (2021-09-18)


## v0.36.4 (2021-09-16)


## v0.36.3 (2021-09-14)


## v0.36.2 (2021-08-30)


## v0.36.1 (2021-08-29)


## v0.36.0 (2021-08-16)


## v0.35.1 (2021-08-15)


## v0.35.0 (2021-08-13)


## v0.34.3 (2021-08-09)


## v0.34.2 (2021-08-09)


## v0.34.1 (2021-08-08)


## v0.34.0 (2021-08-08)


## v0.33.4 (2021-08-06)


## v0.33.3 (2021-08-05)


## v0.33.2 (2021-07-28)


## v0.33.1 (2021-07-18)


## v0.33.0 (2021-07-18)


## v0.32.1 (2021-07-05)


## v0.32.0 (2021-06-30)


## v0.29.0 (2021-03-25)


## v0.28.8 (2021-01-04)


## v0.28.7 (2020-12-13)


## v0.28.6 (2020-10-13)


## v0.28.5 (2020-09-11)


## v0.28.4 (2020-09-06)


## v0.28.3 (2020-08-31)


## v0.28.2 (2020-08-27)


## v0.28.1 (2020-08-17)


## v0.28.0 (2020-07-07)


## v0.27.1 (2020-06-05)


## v0.27.0 (2020-05-27)


## v0.26.3 (2020-05-26)


## v0.26.1 (2020-05-06)


## v0.26.0 (2020-04-26)


## v0.25.1 (2020-04-14)


## v0.25.0 (2020-04-03)


## v0.24.5 (2020-03-08)


## v0.24.4 (2019-12-30)


## v0.24.3 (2019-12-23)


## v0.24.2 (2019-12-17)


## v0.24.1 (2019-12-16)


## v0.24.0 (2019-11-19)


## v0.23.0 (2019-06-04)


## v0.22.0 (2019-04-27)


## v0.21.3 (2018-09-21)


## v0.21.2 (2018-09-20)


## v0.21.1 (2018-09-17)


## v0.21.0 (2018-09-16)


## v0.20.0 (2018-02-21)


## v0.19.1 (2017-06-13)


## v0.19.0 (2017-03-21)


## v0.18.0 (2017-02-03)


## v0.17.7 (2017-02-01)


## v0.17.6 (2016-07-08)

### Testing

- Added test for DNS-SD subtype discovery
  ([`914241b`](https://github.com/python-zeroconf/python-zeroconf/commit/914241b92c3097669e1e8c1a380f6c2f23a14cf8))


## v0.17.5 (2016-03-14)


## v0.17.4 (2015-09-22)


## v0.17.3 (2015-08-19)


## v0.17.2 (2015-07-12)


## v0.17.1 (2015-04-10)


## v0.17.0 (2015-04-10)


## v0.15.1 (2014-07-10)
