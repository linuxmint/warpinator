# Changelog

<!--next-version-placeholder-->

## v0.115.2 (2023-10-05)

### Fix

* Ensure ServiceInfo cache is cleared when adding to the registry ([#1279](https://github.com/python-zeroconf/python-zeroconf/issues/1279)) ([`2060eb2`](https://github.com/python-zeroconf/python-zeroconf/commit/2060eb2cc43489c34bea08924c3f40b875d5a498))

## v0.115.1 (2023-10-01)

### Fix

* Add missing python definition for addresses_by_version ([#1278](https://github.com/python-zeroconf/python-zeroconf/issues/1278)) ([`52ee02b`](https://github.com/python-zeroconf/python-zeroconf/commit/52ee02b16860e344c402124f4b2e2869536ec839))

## v0.115.0 (2023-09-26)

### Feature

* Speed up outgoing multicast queue ([#1277](https://github.com/python-zeroconf/python-zeroconf/issues/1277)) ([`a13fd49`](https://github.com/python-zeroconf/python-zeroconf/commit/a13fd49d77474fd5858de809e48cbab1ccf89173))

## v0.114.0 (2023-09-25)

### Feature

* Speed up responding to queries ([#1275](https://github.com/python-zeroconf/python-zeroconf/issues/1275)) ([`3c6b18c`](https://github.com/python-zeroconf/python-zeroconf/commit/3c6b18cdf4c94773ad6f4497df98feb337939ee9))

## v0.113.0 (2023-09-24)

### Feature

* Improve performance of loading records from cache in ServiceInfo ([#1274](https://github.com/python-zeroconf/python-zeroconf/issues/1274)) ([`6257d49`](https://github.com/python-zeroconf/python-zeroconf/commit/6257d49952e02107f800f4ad4894716508edfcda))

## v0.112.0 (2023-09-14)

### Feature

* Improve AsyncServiceBrowser performance ([#1273](https://github.com/python-zeroconf/python-zeroconf/issues/1273)) ([`0c88ecf`](https://github.com/python-zeroconf/python-zeroconf/commit/0c88ecf5ef6b9b256f991e7a630048de640999a6))

## v0.111.0 (2023-09-14)

### Feature

* Speed up question and answer internals ([#1272](https://github.com/python-zeroconf/python-zeroconf/issues/1272)) ([`d24722b`](https://github.com/python-zeroconf/python-zeroconf/commit/d24722bfa4201d48ab482d35b0ef004f070ada80))

## v0.110.0 (2023-09-14)

### Feature

* Small speed ups to ServiceBrowser ([#1271](https://github.com/python-zeroconf/python-zeroconf/issues/1271)) ([`22c433d`](https://github.com/python-zeroconf/python-zeroconf/commit/22c433ddaea3049ac49933325ba938fd87a529c0))

## v0.109.0 (2023-09-14)

### Feature

* Speed up ServiceBrowsers with a cython pxd ([#1270](https://github.com/python-zeroconf/python-zeroconf/issues/1270)) ([`4837876`](https://github.com/python-zeroconf/python-zeroconf/commit/48378769c3887b5746ca00de30067a4c0851765c))

## v0.108.0 (2023-09-11)

### Feature

* Improve performance of constructing outgoing queries ([#1267](https://github.com/python-zeroconf/python-zeroconf/issues/1267)) ([`00c439a`](https://github.com/python-zeroconf/python-zeroconf/commit/00c439a6400b7850ef9fdd75bc8d82d4e64b1da0))

## v0.107.0 (2023-09-11)

### Feature

* Speed up responding to queries ([#1266](https://github.com/python-zeroconf/python-zeroconf/issues/1266)) ([`24a0a00`](https://github.com/python-zeroconf/python-zeroconf/commit/24a0a00b3e457979e279a2eeadc8fad2ab09e125))

## v0.106.0 (2023-09-11)

### Feature

* Speed up answering questions ([#1265](https://github.com/python-zeroconf/python-zeroconf/issues/1265)) ([`37bfaf2`](https://github.com/python-zeroconf/python-zeroconf/commit/37bfaf2f630358e8c68652f3b3120931a6f94910))

## v0.105.0 (2023-09-10)

### Feature

* Speed up ServiceInfo with a cython pxd ([#1264](https://github.com/python-zeroconf/python-zeroconf/issues/1264)) ([`7ca690a`](https://github.com/python-zeroconf/python-zeroconf/commit/7ca690ac3fa75e7474d3412944bbd5056cb313dd))

## v0.104.0 (2023-09-10)

### Feature

* Speed up generating answers ([#1262](https://github.com/python-zeroconf/python-zeroconf/issues/1262)) ([`50a8f06`](https://github.com/python-zeroconf/python-zeroconf/commit/50a8f066b6ab90bc9e3300f81cf9332550b720df))

## v0.103.0 (2023-09-09)

### Feature

* Avoid calling get_running_loop when resolving ServiceInfo ([#1261](https://github.com/python-zeroconf/python-zeroconf/issues/1261)) ([`33a2714`](https://github.com/python-zeroconf/python-zeroconf/commit/33a2714cadff96edf016b869cc63b0661d16ef2c))

## v0.102.0 (2023-09-07)

### Feature

* Significantly speed up writing outgoing dns records ([#1260](https://github.com/python-zeroconf/python-zeroconf/issues/1260)) ([`bf2f366`](https://github.com/python-zeroconf/python-zeroconf/commit/bf2f3660a1f341e50ab0ae586dfbacbc5ddcc077))

## v0.101.0 (2023-09-07)

### Feature

* Speed up writing outgoing dns records ([#1259](https://github.com/python-zeroconf/python-zeroconf/issues/1259)) ([`248655f`](https://github.com/python-zeroconf/python-zeroconf/commit/248655f0276223b089373c70ec13a0385dfaa4d6))

## v0.100.0 (2023-09-07)

### Feature

* Small speed up to writing outgoing dns records ([#1258](https://github.com/python-zeroconf/python-zeroconf/issues/1258)) ([`1ed6bd2`](https://github.com/python-zeroconf/python-zeroconf/commit/1ed6bd2ec4db0612b71384f923ffff1efd3ce878))

## v0.99.0 (2023-09-06)

### Feature

* Reduce IP Address parsing overhead in ServiceInfo ([#1257](https://github.com/python-zeroconf/python-zeroconf/issues/1257)) ([`83d0b7f`](https://github.com/python-zeroconf/python-zeroconf/commit/83d0b7fda2eb09c9c6e18b85f329d1ddc701e3fb))

## v0.98.0 (2023-09-06)

### Feature

* Speed up decoding incoming packets ([#1256](https://github.com/python-zeroconf/python-zeroconf/issues/1256)) ([`ac081cf`](https://github.com/python-zeroconf/python-zeroconf/commit/ac081cf00addde1ceea2c076f73905fdb293de3a))

## v0.97.0 (2023-09-03)

### Feature

* Speed up answering queries ([#1255](https://github.com/python-zeroconf/python-zeroconf/issues/1255)) ([`2d3aed3`](https://github.com/python-zeroconf/python-zeroconf/commit/2d3aed36e24c73013fcf4acc90803fc1737d0917))

## v0.96.0 (2023-09-03)

### Feature

* Optimize DNSCache.get_by_details ([#1254](https://github.com/python-zeroconf/python-zeroconf/issues/1254)) ([`ce59787`](https://github.com/python-zeroconf/python-zeroconf/commit/ce59787a170781ffdaa22425018d288b395ac081))

## v0.95.0 (2023-09-03)

### Feature

* Speed up adding and removing RecordUpdateListeners ([#1253](https://github.com/python-zeroconf/python-zeroconf/issues/1253)) ([`22e4a29`](https://github.com/python-zeroconf/python-zeroconf/commit/22e4a296d440b3038c0ff5ed6fc8878304ec4937))

## v0.94.0 (2023-09-03)

### Feature

* Optimize cache implementation ([#1252](https://github.com/python-zeroconf/python-zeroconf/issues/1252)) ([`8d3ec79`](https://github.com/python-zeroconf/python-zeroconf/commit/8d3ec792277aaf7ef790318b5b35ab00839ca3b3))

## v0.93.1 (2023-09-03)

### Fix

* No change re-release due to unrecoverable failed CI run ([#1251](https://github.com/python-zeroconf/python-zeroconf/issues/1251)) ([`730921b`](https://github.com/python-zeroconf/python-zeroconf/commit/730921b155dfb9c62251c8c643b1302e807aff3b))

## v0.93.0 (2023-09-02)

### Feature

* Reduce overhead to answer questions ([#1250](https://github.com/python-zeroconf/python-zeroconf/issues/1250)) ([`7cb8da0`](https://github.com/python-zeroconf/python-zeroconf/commit/7cb8da0c6c5c944588009fe36012c1197c422668))

## v0.92.0 (2023-09-02)

### Feature

* Cache construction of records used to answer queries from the service registry ([#1243](https://github.com/python-zeroconf/python-zeroconf/issues/1243)) ([`0890f62`](https://github.com/python-zeroconf/python-zeroconf/commit/0890f628dbbd577fb77d3e6f2e267052b2b2b515))

## v0.91.1 (2023-09-02)

### Fix

* Remove useless calls in ServiceInfo ([#1248](https://github.com/python-zeroconf/python-zeroconf/issues/1248)) ([`4e40fae`](https://github.com/python-zeroconf/python-zeroconf/commit/4e40fae20bf50b4608e28fad4a360c4ed48ac86b))

## v0.91.0 (2023-09-02)

### Feature

* Reduce overhead to process incoming updates by avoiding the handle_response shim ([#1247](https://github.com/python-zeroconf/python-zeroconf/issues/1247)) ([`5e31f0a`](https://github.com/python-zeroconf/python-zeroconf/commit/5e31f0afe4c341fbdbbbe50348a829ea553cbda0))

## v0.90.0 (2023-09-02)

### Feature

* Avoid python float conversion in listener hot path ([#1245](https://github.com/python-zeroconf/python-zeroconf/issues/1245)) ([`816ad4d`](https://github.com/python-zeroconf/python-zeroconf/commit/816ad4dceb3859bad4bb136bdb1d1ee2daa0bf5a))

## v0.89.0 (2023-09-02)

### Feature

* Reduce overhead to process incoming questions ([#1244](https://github.com/python-zeroconf/python-zeroconf/issues/1244)) ([`18b65d1`](https://github.com/python-zeroconf/python-zeroconf/commit/18b65d1c75622869b0c29258215d3db3ae520d6c))

## v0.88.0 (2023-08-29)

### Feature

* Speed up RecordManager with additional cython defs ([#1242](https://github.com/python-zeroconf/python-zeroconf/issues/1242)) ([`5a76fc5`](https://github.com/python-zeroconf/python-zeroconf/commit/5a76fc5ff74f2941ffbf7570e45390f35e0b7e01))

## v0.87.0 (2023-08-29)

### Feature

* Improve performance by adding cython pxd for RecordManager ([#1241](https://github.com/python-zeroconf/python-zeroconf/issues/1241)) ([`a7dad3d`](https://github.com/python-zeroconf/python-zeroconf/commit/a7dad3d9743586f352e21eea1e129c6875f9a713))

## v0.86.0 (2023-08-28)

### Feature

* Build wheels for cpython 3.12 ([#1239](https://github.com/python-zeroconf/python-zeroconf/issues/1239)) ([`58bc154`](https://github.com/python-zeroconf/python-zeroconf/commit/58bc154f55b06b4ddfc4a141592488abe76f062a))
* Use server_key when processing DNSService records ([#1238](https://github.com/python-zeroconf/python-zeroconf/issues/1238)) ([`cc8feb1`](https://github.com/python-zeroconf/python-zeroconf/commit/cc8feb110fefc3fb714fd482a52f16e2b620e8c4))

## v0.85.0 (2023-08-27)

### Feature

* Simplify code to unpack properties ([#1237](https://github.com/python-zeroconf/python-zeroconf/issues/1237)) ([`68d9998`](https://github.com/python-zeroconf/python-zeroconf/commit/68d99985a0e9d2c72ff670b2e2af92271a6fe934))

## v0.84.0 (2023-08-27)

### Feature

* Context managers in ServiceBrowser and AsyncServiceBrowser ([#1233](https://github.com/python-zeroconf/python-zeroconf/issues/1233)) ([`bd8d846`](https://github.com/python-zeroconf/python-zeroconf/commit/bd8d8467dec2a39a0b525043ea1051259100fded))

## v0.83.1 (2023-08-27)

### Fix

* Rebuild wheels with cython 3.0.2 ([#1236](https://github.com/python-zeroconf/python-zeroconf/issues/1236)) ([`dd637fb`](https://github.com/python-zeroconf/python-zeroconf/commit/dd637fb2e5a87ba283750e69d116e124bef54e7c))

## v0.83.0 (2023-08-26)

### Feature

* Speed up question and answer history with a cython pxd ([#1234](https://github.com/python-zeroconf/python-zeroconf/issues/1234)) ([`703ecb2`](https://github.com/python-zeroconf/python-zeroconf/commit/703ecb2901b2150fb72fac3deed61d7302561298))

## v0.82.1 (2023-08-22)

### Fix

* Build failures with older cython 0.29 series ([#1232](https://github.com/python-zeroconf/python-zeroconf/issues/1232)) ([`30c3ad9`](https://github.com/python-zeroconf/python-zeroconf/commit/30c3ad9d1bc6b589e1ca6675fea21907ebcd1ced))

## v0.82.0 (2023-08-22)

### Feature

* Optimize processing of records in RecordUpdateListener subclasses ([#1231](https://github.com/python-zeroconf/python-zeroconf/issues/1231)) ([`3e89294`](https://github.com/python-zeroconf/python-zeroconf/commit/3e89294ea0ecee1122e1c1ffdc78925add8ca40e))

## v0.81.0 (2023-08-22)

### Feature

* Speed up the service registry with a cython pxd ([#1226](https://github.com/python-zeroconf/python-zeroconf/issues/1226)) ([`47d3c7a`](https://github.com/python-zeroconf/python-zeroconf/commit/47d3c7ad4bc5f2247631c3ad5e6b6156d45a0a4e))
* Optimizing sending answers to questions ([#1227](https://github.com/python-zeroconf/python-zeroconf/issues/1227)) ([`cd7b56b`](https://github.com/python-zeroconf/python-zeroconf/commit/cd7b56b2aa0c8ee429da430e9a36abd515512011))

## v0.80.0 (2023-08-15)

### Feature

* Optimize unpacking properties in ServiceInfo ([#1225](https://github.com/python-zeroconf/python-zeroconf/issues/1225)) ([`1492e41`](https://github.com/python-zeroconf/python-zeroconf/commit/1492e41b3d5cba5598cc9dd6bd2bc7d238f13555))

## v0.79.0 (2023-08-14)

### Feature

* Refactor notify implementation to reduce overhead of adding and removing listeners ([#1224](https://github.com/python-zeroconf/python-zeroconf/issues/1224)) ([`ceb92cf`](https://github.com/python-zeroconf/python-zeroconf/commit/ceb92cfe42d885dbb38cee7aaeebf685d97627a9))

## v0.78.0 (2023-08-14)

### Feature

* Add cython pxd file for _listener.py to improve incoming message processing performance ([#1221](https://github.com/python-zeroconf/python-zeroconf/issues/1221)) ([`f459856`](https://github.com/python-zeroconf/python-zeroconf/commit/f459856a0a61b8afa8a541926d7e15d51f8e4aea))

## v0.77.0 (2023-08-14)

### Feature

* Cythonize _listener.py to improve incoming message processing performance ([#1220](https://github.com/python-zeroconf/python-zeroconf/issues/1220)) ([`9efde8c`](https://github.com/python-zeroconf/python-zeroconf/commit/9efde8c8c1ed14c5d3c162f185b49212fcfcb5c9))

## v0.76.0 (2023-08-14)

### Feature

* Improve performance responding to queries ([#1217](https://github.com/python-zeroconf/python-zeroconf/issues/1217)) ([`69b33be`](https://github.com/python-zeroconf/python-zeroconf/commit/69b33be3b2f9d4a27ef5154cae94afca048efffa))

## v0.75.0 (2023-08-13)

### Feature

* Expose flag to disable strict name checking in service registration ([#1215](https://github.com/python-zeroconf/python-zeroconf/issues/1215)) ([`5df8a57`](https://github.com/python-zeroconf/python-zeroconf/commit/5df8a57a14d59687a3c22ea8ee063e265031e278))
* Speed up processing incoming records ([#1216](https://github.com/python-zeroconf/python-zeroconf/issues/1216)) ([`aff625d`](https://github.com/python-zeroconf/python-zeroconf/commit/aff625dc6a5e816dad519644c4adac4f96980c04))

## v0.74.0 (2023-08-04)

### Feature

* Speed up unpacking text records in ServiceInfo ([#1212](https://github.com/python-zeroconf/python-zeroconf/issues/1212)) ([`99a6f98`](https://github.com/python-zeroconf/python-zeroconf/commit/99a6f98e44a1287ba537eabb852b1b69923402f0))

### Fix

* Remove typing on reset_ttl for cython compat ([#1213](https://github.com/python-zeroconf/python-zeroconf/issues/1213)) ([`0094e26`](https://github.com/python-zeroconf/python-zeroconf/commit/0094e2684344c6b7edd7948924f093f1b4c19901))

## v0.73.0 (2023-08-03)

### Feature

* Add a cache to service_type_name ([#1211](https://github.com/python-zeroconf/python-zeroconf/issues/1211)) ([`53a694f`](https://github.com/python-zeroconf/python-zeroconf/commit/53a694f60e675ae0560e727be6b721b401c2b68f))

## v0.72.3 (2023-08-03)

### Fix

* Revert adding typing to DNSRecord.suppressed_by ([#1210](https://github.com/python-zeroconf/python-zeroconf/issues/1210)) ([`3dba5ae`](https://github.com/python-zeroconf/python-zeroconf/commit/3dba5ae0c0e9473b7b20fd6fc79fa1a3b298dc5a))

## v0.72.2 (2023-08-03)

### Fix

* Revert DNSIncoming cimport in _dns.pxd ([#1209](https://github.com/python-zeroconf/python-zeroconf/issues/1209)) ([`5f14b6d`](https://github.com/python-zeroconf/python-zeroconf/commit/5f14b6dc687b3a0716d0ca7f61ccf1e93dfe5fa1))

## v0.72.1 (2023-08-03)

### Fix

* Race with InvalidStateError when async_request times out ([#1208](https://github.com/python-zeroconf/python-zeroconf/issues/1208)) ([`2233b6b`](https://github.com/python-zeroconf/python-zeroconf/commit/2233b6bc4ceeee5524d2ee88ecae8234173feb5f))

## v0.72.0 (2023-08-02)

### Feature

* Speed up processing incoming records ([#1206](https://github.com/python-zeroconf/python-zeroconf/issues/1206)) ([`126849c`](https://github.com/python-zeroconf/python-zeroconf/commit/126849c92be8cec9253fba9faa591029d992fcc3))

## v0.71.5 (2023-08-02)

### Fix

* Improve performance of ServiceInfo.async_request ([#1205](https://github.com/python-zeroconf/python-zeroconf/issues/1205)) ([`8019a73`](https://github.com/python-zeroconf/python-zeroconf/commit/8019a73c952f2fc4c88d849aab970fafedb316d8))

## v0.71.4 (2023-07-24)

### Fix

* Cleanup naming from previous refactoring in ServiceInfo ([#1202](https://github.com/python-zeroconf/python-zeroconf/issues/1202)) ([`b272d75`](https://github.com/python-zeroconf/python-zeroconf/commit/b272d75abd982f3be1f4b20f683cac38011cc6f4))

## v0.71.3 (2023-07-23)

### Fix

* Pin python-semantic-release to fix release process ([#1200](https://github.com/python-zeroconf/python-zeroconf/issues/1200)) ([`c145a23`](https://github.com/python-zeroconf/python-zeroconf/commit/c145a238d768aa17c3aebe120c20a46bfbec6b99))

## v0.71.2 (2023-07-23)

### Fix

* No change re-release to fix wheel builds ([#1199](https://github.com/python-zeroconf/python-zeroconf/issues/1199)) ([`8c3a4c8`](https://github.com/python-zeroconf/python-zeroconf/commit/8c3a4c80c221bea7401c12e1c6a525e75b7ffea2))

## v0.71.1 (2023-07-23)

### Fix

* Add missing if TYPE_CHECKING guard to generate_service_query ([#1198](https://github.com/python-zeroconf/python-zeroconf/issues/1198)) ([`ac53adf`](https://github.com/python-zeroconf/python-zeroconf/commit/ac53adf7e71db14c1a0f9adbfd1d74033df36898))

## v0.71.0 (2023-07-08)

### Feature

* Improve incoming data processing performance ([#1194](https://github.com/python-zeroconf/python-zeroconf/issues/1194)) ([`a56c776`](https://github.com/python-zeroconf/python-zeroconf/commit/a56c776008ef86f99db78f5997e45a57551be725))

## v0.70.0 (2023-07-02)

### Feature

* Add support for sending to a specific `addr` and `port` with `ServiceInfo.async_request` and `ServiceInfo.request` ([#1192](https://github.com/python-zeroconf/python-zeroconf/issues/1192)) ([`405f547`](https://github.com/python-zeroconf/python-zeroconf/commit/405f54762d3f61e97de9c1787e837e953de31412))

## v0.69.0 (2023-06-18)

### Feature

* Cython3 support ([#1190](https://github.com/python-zeroconf/python-zeroconf/issues/1190)) ([`8ae8ba1`](https://github.com/python-zeroconf/python-zeroconf/commit/8ae8ba1af324b0c8c2da3bd12c264a5c0f3dcc3d))
* Reorder incoming data handler to reduce overhead ([#1189](https://github.com/python-zeroconf/python-zeroconf/issues/1189)) ([`32756ff`](https://github.com/python-zeroconf/python-zeroconf/commit/32756ff113f675b7a9cf16d3c0ab840ba733e5e4))

## v0.68.1 (2023-06-18)

### Fix

* Reduce debug logging overhead by adding missing checks to datagram_received ([#1188](https://github.com/python-zeroconf/python-zeroconf/issues/1188)) ([`ac5c50a`](https://github.com/python-zeroconf/python-zeroconf/commit/ac5c50afc70aaa33fcd20bf02222ff4f0c596fa3))

## v0.68.0 (2023-06-17)

### Feature

* Reduce overhead to handle queries and responses ([#1184](https://github.com/python-zeroconf/python-zeroconf/issues/1184)) ([`81126b7`](https://github.com/python-zeroconf/python-zeroconf/commit/81126b7600f94848ef8c58b70bac0c6ab993c6ae))

## v0.67.0 (2023-06-17)

### Feature

* Speed up answering incoming questions ([#1186](https://github.com/python-zeroconf/python-zeroconf/issues/1186)) ([`8f37665`](https://github.com/python-zeroconf/python-zeroconf/commit/8f376658d2a3bef0353646e6fddfda15626b73a9))

## v0.66.0 (2023-06-13)
### Feature
* Optimize construction of outgoing dns records ([#1182](https://github.com/python-zeroconf/python-zeroconf/issues/1182)) ([`fc0341f`](https://github.com/python-zeroconf/python-zeroconf/commit/fc0341f281cdb71428c0f1cf90c12d34cbb4acae))

## v0.65.0 (2023-06-13)
### Feature
* Reduce overhead to enumerate ip addresses in ServiceInfo ([#1181](https://github.com/python-zeroconf/python-zeroconf/issues/1181)) ([`6a85cbf`](https://github.com/python-zeroconf/python-zeroconf/commit/6a85cbf2b872cb0abd184c2dd728d9ae3eb8115c))

## v0.64.1 (2023-06-05)
### Fix
* Small internal typing cleanups ([#1180](https://github.com/python-zeroconf/python-zeroconf/issues/1180)) ([`f03e511`](https://github.com/python-zeroconf/python-zeroconf/commit/f03e511f7aae72c5ccd4f7514d89e168847bd7a2))

## v0.64.0 (2023-06-05)
### Feature
* Speed up processing incoming records ([#1179](https://github.com/python-zeroconf/python-zeroconf/issues/1179)) ([`d919316`](https://github.com/python-zeroconf/python-zeroconf/commit/d9193160b05beeca3755e19fd377ba13fe37b071))

### Fix
* Always answer QU questions when the exact same packet is received from different sources in sequence ([#1178](https://github.com/python-zeroconf/python-zeroconf/issues/1178)) ([`74d7ba1`](https://github.com/python-zeroconf/python-zeroconf/commit/74d7ba1aeeae56be087ee8142ee6ca1219744baa))

## v0.63.0 (2023-05-25)
### Feature
* Small speed up to fetch dns addresses from ServiceInfo ([#1176](https://github.com/python-zeroconf/python-zeroconf/issues/1176)) ([`4deaa6e`](https://github.com/python-zeroconf/python-zeroconf/commit/4deaa6ed7c9161db55bf16ec068ab7260bbd4976))
* Speed up the service registry ([#1174](https://github.com/python-zeroconf/python-zeroconf/issues/1174)) ([`360ceb2`](https://github.com/python-zeroconf/python-zeroconf/commit/360ceb2548c4c4974ff798aac43a6fff9803ea0e))
* Improve dns cache performance ([#1172](https://github.com/python-zeroconf/python-zeroconf/issues/1172)) ([`bb496a1`](https://github.com/python-zeroconf/python-zeroconf/commit/bb496a1dd5fa3562c0412cb064d14639a542592e))

## v0.62.0 (2023-05-04)
### Feature
* Improve performance of ServiceBrowser outgoing query scheduler ([#1170](https://github.com/python-zeroconf/python-zeroconf/issues/1170)) ([`963d022`](https://github.com/python-zeroconf/python-zeroconf/commit/963d022ef82b615540fa7521d164a98a6c6f5209))

## v0.61.0 (2023-05-03)
### Feature
* Speed up parsing NSEC records ([#1169](https://github.com/python-zeroconf/python-zeroconf/issues/1169)) ([`06fa94d`](https://github.com/python-zeroconf/python-zeroconf/commit/06fa94d87b4f0451cb475a921ce1d8e9562e0f26))

## v0.60.0 (2023-05-01)
### Feature
* Speed up processing incoming data ([#1167](https://github.com/python-zeroconf/python-zeroconf/issues/1167)) ([`fbaaf7b`](https://github.com/python-zeroconf/python-zeroconf/commit/fbaaf7bb6ff985bdabb85feb6cba144f12d4f1d6))

## v0.59.0 (2023-05-01)
### Feature
* Speed up decoding dns questions when processing incoming data ([#1168](https://github.com/python-zeroconf/python-zeroconf/issues/1168)) ([`f927190`](https://github.com/python-zeroconf/python-zeroconf/commit/f927190cb24f70fd7c825c6e12151fcc0daf3973))

## v0.58.2 (2023-04-26)
### Fix
* Re-release to rebuild failed wheels ([#1165](https://github.com/python-zeroconf/python-zeroconf/issues/1165)) ([`4986271`](https://github.com/python-zeroconf/python-zeroconf/commit/498627166a4976f1d9d8cd1f3654b0d50272d266))

## v0.58.1 (2023-04-26)
### Fix
* Reduce cast calls in service browser ([#1164](https://github.com/python-zeroconf/python-zeroconf/issues/1164)) ([`c0d65ae`](https://github.com/python-zeroconf/python-zeroconf/commit/c0d65aeae7037a18ed1149336f5e7bdb8b2dd8cf))

## v0.58.0 (2023-04-23)
### Feature
* Speed up incoming parser ([#1163](https://github.com/python-zeroconf/python-zeroconf/issues/1163)) ([`4626399`](https://github.com/python-zeroconf/python-zeroconf/commit/46263999c0c7ea5176885f1eadd2c8498834b70e))

## v0.57.0 (2023-04-23)
### Feature
* Speed up incoming data parser ([#1161](https://github.com/python-zeroconf/python-zeroconf/issues/1161)) ([`cb4c3b2`](https://github.com/python-zeroconf/python-zeroconf/commit/cb4c3b2b80ca3b88b8de6e87062a45e03e8805a6))

## v0.56.0 (2023-04-07)
### Feature
* Reduce denial of service protection overhead ([#1157](https://github.com/python-zeroconf/python-zeroconf/issues/1157)) ([`2c2f26a`](https://github.com/python-zeroconf/python-zeroconf/commit/2c2f26a87d0aac81a77205b06bc9ba499caa2321))

## v0.55.0 (2023-04-07)
### Feature
* Improve performance of processing incoming records ([#1155](https://github.com/python-zeroconf/python-zeroconf/issues/1155)) ([`b65e279`](https://github.com/python-zeroconf/python-zeroconf/commit/b65e2792751c44e0fafe9ad3a55dadc5d8ee9d46))

## v0.54.0 (2023-04-03)
### Feature
* Avoid waking async_request when record updates are not relevant ([#1153](https://github.com/python-zeroconf/python-zeroconf/issues/1153)) ([`a3f970c`](https://github.com/python-zeroconf/python-zeroconf/commit/a3f970c7f66067cf2c302c49ed6ad8286f19b679))

## v0.53.1 (2023-04-03)
### Fix
* Addresses incorrect after server name change ([#1154](https://github.com/python-zeroconf/python-zeroconf/issues/1154)) ([`41ea06a`](https://github.com/python-zeroconf/python-zeroconf/commit/41ea06a0192c0d186e678009285759eb37d880d5))

## v0.53.0 (2023-04-02)
### Feature
* Improve ServiceBrowser performance by removing OrderedDict ([#1148](https://github.com/python-zeroconf/python-zeroconf/issues/1148)) ([`9a16be5`](https://github.com/python-zeroconf/python-zeroconf/commit/9a16be56a9f69a5d0f7cde13dc1337b6d93c1433))

### Fix
* Make parsed_scoped_addresses return addresses in the same order as all other methods ([#1150](https://github.com/python-zeroconf/python-zeroconf/issues/1150)) ([`9b6adcf`](https://github.com/python-zeroconf/python-zeroconf/commit/9b6adcf5c04a469632ee866c32f5898c5cbf810a))

### Technically breaking change
* IP Addresses returned from `ServiceInfo.parsed_addresses` are now stringified using the python `ipaddress` library which may format them differently than `socket.inet_ntop` depending on the operating system. It is recommended to use `ServiceInfo.ip_addresses_by_version` instead going forward as it offers a stronger guarantee since it returns `ipaddress` objects.

## v0.52.0 (2023-04-02)
### Feature
* Small cleanups to cache cleanup interval ([#1146](https://github.com/python-zeroconf/python-zeroconf/issues/1146)) ([`b434b60`](https://github.com/python-zeroconf/python-zeroconf/commit/b434b60f14ebe8f114b7b19bb4f54081c8ae0173))
* Add ip_addresses_by_version to ServiceInfo ([#1145](https://github.com/python-zeroconf/python-zeroconf/issues/1145)) ([`524494e`](https://github.com/python-zeroconf/python-zeroconf/commit/524494edd49bd049726b19ae8ac8f6eea69a3943))
* Speed up processing records in the ServiceBrowser ([#1143](https://github.com/python-zeroconf/python-zeroconf/issues/1143)) ([`6a327d0`](https://github.com/python-zeroconf/python-zeroconf/commit/6a327d00ffb81de55b7c5b599893c789996680c1))
* Speed up matching types in the ServiceBrowser ([#1144](https://github.com/python-zeroconf/python-zeroconf/issues/1144)) ([`68871c3`](https://github.com/python-zeroconf/python-zeroconf/commit/68871c3b5569e41740a66b7d3d7fa5cc41514ea5))
* Include tests and docs in sdist archives ([#1142](https://github.com/python-zeroconf/python-zeroconf/issues/1142)) ([`da10a3b`](https://github.com/python-zeroconf/python-zeroconf/commit/da10a3b2827cee0719d3bb9152ae897f061c6e2e))

## v0.51.0 (2023-04-01)
### Feature
* Improve performance of constructing ServiceInfo ([#1141](https://github.com/python-zeroconf/python-zeroconf/issues/1141)) ([`36d5b45`](https://github.com/python-zeroconf/python-zeroconf/commit/36d5b45a4ece1dca902e9c3c79b5a63b8d9ae41f))

## v0.50.0 (2023-04-01)
### Feature
* Small speed up to handler dispatch ([#1140](https://github.com/python-zeroconf/python-zeroconf/issues/1140)) ([`5bd1b6e`](https://github.com/python-zeroconf/python-zeroconf/commit/5bd1b6e7b4dd796069461c737ded956305096307))

## v0.49.0 (2023-04-01)
### Feature
* Speed up processing incoming records ([#1139](https://github.com/python-zeroconf/python-zeroconf/issues/1139)) ([`7246a34`](https://github.com/python-zeroconf/python-zeroconf/commit/7246a344b6c0543871b40715c95c9435db4c7f81))

## v0.48.0 (2023-04-01)
### Feature
* Reduce overhead to send responses ([#1135](https://github.com/python-zeroconf/python-zeroconf/issues/1135)) ([`c4077dd`](https://github.com/python-zeroconf/python-zeroconf/commit/c4077dde6dfde9e2598eb63daa03c36063a3e7b0))

## v0.47.4 (2023-03-20)
### Fix
* Correct duplicate record entries in windows wheels by updating poetry-core ([#1134](https://github.com/python-zeroconf/python-zeroconf/issues/1134)) ([`a43055d`](https://github.com/python-zeroconf/python-zeroconf/commit/a43055d3fa258cd762c3e9394b01f8bdcb24f97e))

## v0.47.3 (2023-02-14)
### Fix
* Hold a strong reference to the query sender start task ([#1128](https://github.com/python-zeroconf/python-zeroconf/issues/1128)) ([`808c3b2`](https://github.com/python-zeroconf/python-zeroconf/commit/808c3b2194a7f499a469a9893102d328ccee83db))

## v0.47.2 (2023-02-14)
### Fix
* Missing c extensions with newer poetry ([#1129](https://github.com/python-zeroconf/python-zeroconf/issues/1129)) ([`44d7fc6`](https://github.com/python-zeroconf/python-zeroconf/commit/44d7fc6483485102f60c91d591d0d697872f8865))

## v0.47.1 (2022-12-24)
### Fix
* The equality checks for DNSPointer and DNSService should be case insensitive ([#1122](https://github.com/python-zeroconf/python-zeroconf/issues/1122)) ([`48ae77f`](https://github.com/python-zeroconf/python-zeroconf/commit/48ae77f026a96e2ca475b0ff80cb6d22207ce52f))

## v0.47.0 (2022-12-22)
### Feature
* Optimize equality checks for DNS records ([#1120](https://github.com/python-zeroconf/python-zeroconf/issues/1120)) ([`3a25ff7`](https://github.com/python-zeroconf/python-zeroconf/commit/3a25ff74bea83cd7d50888ce1ebfd7650d704bfa))

## v0.46.0 (2022-12-21)
### Feature
* Optimize the dns cache ([#1119](https://github.com/python-zeroconf/python-zeroconf/issues/1119)) ([`e80fcef`](https://github.com/python-zeroconf/python-zeroconf/commit/e80fcef967024f8e846e44b464a82a25f5550edf))

## v0.45.0 (2022-12-20)
### Feature
* Optimize construction of outgoing packets ([#1118](https://github.com/python-zeroconf/python-zeroconf/issues/1118)) ([`81e186d`](https://github.com/python-zeroconf/python-zeroconf/commit/81e186d365c018381f9b486a4dbe4e2e4b8bacbf))

## v0.44.0 (2022-12-18)
### Feature
* Optimize dns objects by adding pxd files ([#1113](https://github.com/python-zeroconf/python-zeroconf/issues/1113)) ([`919d4d8`](https://github.com/python-zeroconf/python-zeroconf/commit/919d4d875747b4fa68e25bccd5aae7f304d8a36d))

## v0.43.0 (2022-12-18)
### Feature
* Optimize incoming parser by reducing call stack ([#1116](https://github.com/python-zeroconf/python-zeroconf/issues/1116)) ([`11f3f0e`](https://github.com/python-zeroconf/python-zeroconf/commit/11f3f0e699e00c1ee3d6d8ab5e30f62525510589))

## v0.42.0 (2022-12-18)
### Feature
* Optimize incoming parser by using unpack_from ([#1115](https://github.com/python-zeroconf/python-zeroconf/issues/1115)) ([`a7d50ba`](https://github.com/python-zeroconf/python-zeroconf/commit/a7d50baab362eadd2d292df08a39de6836b41ea7))

## v0.41.0 (2022-12-18)
### Feature
* Optimize incoming parser by adding pxd files ([#1111](https://github.com/python-zeroconf/python-zeroconf/issues/1111)) ([`26efeb0`](https://github.com/python-zeroconf/python-zeroconf/commit/26efeb09783050266242542228f34eb4dd83e30c))

## v0.40.1 (2022-12-18)
### Fix
* Fix project name in pyproject.toml ([#1112](https://github.com/python-zeroconf/python-zeroconf/issues/1112)) ([`a330f62`](https://github.com/python-zeroconf/python-zeroconf/commit/a330f62040475257c4a983044e1675aeb95e030a))

## v0.40.0 (2022-12-17)
### Feature
* Drop async_timeout requirement for python 3.11+ ([#1107](https://github.com/python-zeroconf/python-zeroconf/issues/1107)) ([`1f4224e`](https://github.com/python-zeroconf/python-zeroconf/commit/1f4224ef122299235013cb81b501f8ff9a30dea1))

# 0.39.5

  - This is a stub version to initialize python-semantic-release

    This version will not be published

# 0.39.4

  - Fix IP changes being missed by ServiceInfo (\#1102) @bdraco

# 0.39.3

  - Fix port changes not being seen by ServiceInfo (\#1100) @bdraco

# 0.39.2

  - Performance improvements for parsing incoming packet data (\#1095)
    (\#1097) @bdraco

# 0.39.1

  - Performance improvements for constructing outgoing packet data
    (\#1090) @bdraco

# 0.39.0

Technically backwards incompatible:

  - Switch to using async\_timeout for timeouts (\#1081) @bdraco
    
    Significantly reduces the number of asyncio tasks that are created
    when using <span class="title-ref">ServiceInfo</span> or
    <span class="title-ref">AsyncServiceInfo</span>

# 0.38.7

  - Performance improvements for parsing incoming packet data (\#1076)
    @bdraco

# 0.38.6

  - Performance improvements for fetching ServiceInfo (\#1068) @bdraco

# 0.38.5

  - Fix ServiceBrowsers not getting ServiceStateChange.Removed callbacks
    on PTR record expire (\#1064) @bdraco
    
    ServiceBrowsers were only getting a
    <span class="title-ref">ServiceStateChange.Removed</span> callback
    when the record was sent with a TTL of 0. ServiceBrowsers now
    correctly get a
    <span class="title-ref">ServiceStateChange.Removed</span> callback
    when the record expires as well.

  - Fix missing minimum version of python 3.7 (\#1060) @stevencrader

# 0.38.4

  - Fix IP Address updates when hostname is uppercase (\#1057) @bdraco
    
    ServiceBrowsers would not callback updates when the ip address
    changed if the hostname contained uppercase characters

# 0.38.3

Version bump only, no changes from 0.38.2

# 0.38.2

  - Make decode errors more helpful in finding the source of the bad
    data (\#1052) @bdraco

# 0.38.1

  - Improve performance of query scheduler (\#1043) @bdraco
  - Avoid linear type searches in ServiceBrowsers (\#1044) @bdraco

# 0.38.0

  - Handle Service types that end with another service type (\#1041)
    @apworks1

Backwards incompatible:

  - Dropped Python 3.6 support (\#1009) @bdraco

# 0.37.0

Technically backwards incompatible:

  - Adding a listener that does not inherit from RecordUpdateListener
    now logs an error (\#1034) @bdraco

  - The NotRunningException exception is now thrown when Zeroconf is not
    running (\#1033) @bdraco
    
    Before this change the consumer would get a timeout or an
    EventLoopBlocked exception when calling
    <span class="title-ref">ServiceInfo.\*request</span> when the
    instance had already been shutdown or had failed to startup.

  - The EventLoopBlocked exception is now thrown when a coroutine times
    out (\#1032) @bdraco
    
    Previously
    <span class="title-ref">concurrent.futures.TimeoutError</span> would
    have been raised instead. This is never expected to happen during
    normal operation.

# 0.36.13

  - Unavailable interfaces are now skipped during socket bind (\#1028)
    @bdraco

  - Downgraded incoming corrupt packet logging to debug (\#1029) @bdraco
    
    Warning about network traffic we have no control over is confusing
    to users as they think there is something wrong with zeroconf

# 0.36.12

  - Prevented service lookups from deadlocking if time abruptly moves
    backwards (\#1006) @bdraco
    
    The typical reason time moves backwards is via an ntp update

# 0.36.11

No functional changes from 0.36.10. This release corrects an error in
the README.rst file that prevented the build from uploading to PyPI

# 0.36.10

  - scope\_id is now stripped from IPv6 addresses if given (\#1020)
    @StevenLooman
    
    cpython 3.9 allows a suffix %scope\_id in IPv6Address. This caused
    an error with the existing code if it was not stripped

  - Optimized decoding labels from incoming packets (\#1019) @bdraco

# 0.36.9

  - Ensure ServiceInfo orders newest addresses first (\#1012) @bdraco
    
    This change effectively restored the behavior before 1s cache flush
    expire behavior described in rfc6762 section 10.2 was added for
    callers that rely on this.

# 0.36.8

  - Fixed ServiceBrowser infinite loop when zeroconf is closed before it
    is canceled (\#1008) @bdraco

# 0.36.7

  - Improved performance of responding to queries (\#994) (\#996)
    (\#997) @bdraco
  - Improved log message when receiving an invalid or corrupt packet
    (\#998) @bdraco

# 0.36.6

  - Improved performance of sending outgoing packets (\#990) @bdraco

# 0.36.5

  - Reduced memory usage for incoming and outgoing packets (\#987)
    @bdraco

# 0.36.4

  - Improved performance of constructing outgoing packets (\#978)
    (\#979) @bdraco
  - Deferred parsing of incoming packets when it can be avoided (\#983)
    @bdraco

# 0.36.3

  - Improved performance of parsing incoming packets (\#975) @bdraco

# 0.36.2

  - Include NSEC records for non-existent types when responding with
    addresses (\#972) (\#971) @bdraco Implements RFC6762 sec 6.2
    (<http://datatracker.ietf.org/doc/html/rfc6762#section-6.2>)

# 0.36.1

  - Skip goodbye packets for addresses when there is another service
    registered with the same name (\#968) @bdraco
    
    If a ServiceInfo that used the same server name as another
    ServiceInfo was unregistered, goodbye packets would be sent for the
    addresses and would cause the other service to be seen as offline.

  - Fixed equality and hash for dns records with the unique bit (\#969)
    @bdraco
    
    These records should have the same hash and equality since the
    unique bit (cache flush bit) is not considered when adding or
    removing the records from the cache.

# 0.36.0

Technically backwards incompatible:

  - Fill incomplete IPv6 tuples to avoid WinError on windows (\#965)
    @lokesh2019
    
    Fixed \#932

# 0.35.1

  - Only reschedule types if the send next time changes (\#958) @bdraco
    
    When the PTR response was seen again, the timer was being canceled
    and rescheduled even if the timer was for the same time. While this
    did not cause any breakage, it is quite inefficient.

  - Cache DNS record and question hashes (\#960) @bdraco
    
    The hash was being recalculated every time the object was being used
    in a set or dict. Since the hashes are effectively immutable, we
    only calculate them once now.

# 0.35.0

  - Reduced chance of accidental synchronization of ServiceInfo requests
    (\#955) @bdraco
  - Sort aggregated responses to increase chance of name compression
    (\#954) @bdraco

Technically backwards incompatible:

  - Send unicast replies on the same socket the query was received
    (\#952) @bdraco
    
    When replying to a QU question, we do not know if the sending host
    is reachable from all of the sending sockets. We now avoid this
    problem by replying via the receiving socket. This was the existing
    behavior when <span class="title-ref">InterfaceChoice.Default</span>
    is set.
    
    This change extends the unicast relay behavior to used with
    <span class="title-ref">InterfaceChoice.Default</span> to apply when
    <span class="title-ref">InterfaceChoice.All</span> or interfaces are
    explicitly passed when instantiating a
    <span class="title-ref">Zeroconf</span> instance.
    
    Fixes \#951

# 0.34.3

  - Fix sending immediate multicast responses (\#949) @bdraco

# 0.34.2

  - Coalesce aggregated multicast answers (\#945) @bdraco
    
    When the random delay is shorter than the last scheduled response,
    answers are now added to the same outgoing time group.
    
    This reduces traffic when we already know we will be sending a group
    of answers inside the random delay window described in
    datatracker.ietf.org/doc/html/rfc6762\#section-6.3

  - Ensure ServiceInfo requests can be answered inside the default
    timeout with network protection (\#946) @bdraco
    
    Adjust the time windows to ensure responses that have triggered the
    protection against against excessive packet flooding due to software
    bugs or malicious attack described in RFC6762 section 6 can respond
    in under 1350ms to ensure ServiceInfo can ask two questions within
    the default timeout of 3000ms

# 0.34.1

  - Ensure multicast aggregation sends responses within 620ms (\#942)
    @bdraco
    
    Responses that trigger the protection against against excessive
    packet flooding due to software bugs or malicious attack described
    in RFC6762 section 6 could cause the multicast aggregation response
    to be delayed longer than 620ms (The maximum random delay of 120ms
    and 500ms additional for aggregation).
    
    Only responses that trigger the protection are delayed longer than
    620ms

# 0.34.0

  - Implemented Multicast Response Aggregation (\#940) @bdraco
    
    Responses are now aggregated when possible per rules in RFC6762
    section 6.4
    
    Responses that trigger the protection against against excessive
    packet flooding due to software bugs or malicious attack described
    in RFC6762 section 6 are delayed instead of discarding as it was
    causing responders that implement Passive Observation Of Failures
    (POOF) to evict the records.
    
    Probe responses are now always sent immediately as there were cases
    where they would fail to be answered in time to defend a name.

# 0.33.4

  - Ensure zeroconf can be loaded when the system disables IPv6 (\#933)
    @che0

# 0.33.3

  - Added support for forward dns compression pointers (\#934) @bdraco
  - Provide sockname when logging a protocol error (\#935) @bdraco

# 0.33.2

  - Handle duplicate goodbye answers in the same packet (\#928) @bdraco
    
    Solves an exception being thrown when we tried to remove the known
    answer from the cache when the second goodbye answer in the same
    packet was processed
    
    Fixed \#926

  - Skip ipv6 interfaces that return ENODEV (\#930) @bdraco

# 0.33.1

  - Version number change only with less restrictive directory
    permissions
    
    Fixed \#923

# 0.33.0

This release eliminates all threading locks as all non-threadsafe
operations now happen in the event loop.

  - Let connection\_lost close the underlying socket (\#918) @bdraco
    
    The socket was closed during shutdown before asyncio's
    connection\_lost handler had a chance to close it which resulted in
    a traceback on windows.
    
    Fixed \#917

Technically backwards incompatible:

  - Removed duplicate unregister\_all\_services code (\#910) @bdraco
    
    Calling Zeroconf.close from same asyncio event loop zeroconf is
    running in will now skip unregister\_all\_services and log a warning
    as this a blocking operation and is not async safe and never has
    been.
    
    Use AsyncZeroconf instead, or for legacy code call
    async\_unregister\_all\_services before Zeroconf.close

# 0.32.1

  - Increased timeout in ServiceInfo.request to handle loaded systems
    (\#895) @bdraco
    
    It can take a few seconds for a loaded system to run the
    <span class="title-ref">async\_request</span> coroutine when the
    event loop is busy, or the system is CPU bound (example being Home
    Assistant startup). We now add an additional
    <span class="title-ref">\_LOADED\_SYSTEM\_TIMEOUT</span> (10s) to
    the <span class="title-ref">run\_coroutine\_threadsafe</span> calls
    to ensure the coroutine has the total amount of time to run up to
    its internal timeout (default of 3000ms).
    
    Ten seconds is a bit large of a timeout; however, it is only used in
    cases where we wrap other timeouts. We now expect the only instance
    the <span class="title-ref">run\_coroutine\_threadsafe</span> result
    timeout will happen in a production circumstance is when someone is
    running a <span class="title-ref">ServiceInfo.request()</span> in a
    thread and another thread calls
    <span class="title-ref">Zeroconf.close()</span> at just the right
    moment that the future is never completed unless the system is so
    loaded that it is nearly unresponsive.
    
    The timeout for
    <span class="title-ref">run\_coroutine\_threadsafe</span> is the
    maximum time a thread can cleanly shut down when zeroconf is closed
    out in another thread, which should always be longer than the
    underlying thread operation.

# 0.32.0

This release offers 100% line and branch coverage.

  - Made ServiceInfo first question QU (\#852) @bdraco
    
    We want an immediate response when requesting with ServiceInfo by
    asking a QU question; most responders will not delay the response
    and respond right away to our question. This also improves
    compatibility with split networks as we may not have been able to
    see the response otherwise. If the responder has not multicast the
    record recently, it may still choose to do so in addition to
    responding via unicast
    
    Reduces traffic when there are multiple zeroconf instances running
    on the network running ServiceBrowsers
    
    If we don't get an answer on the first try, we ask a QM question in
    the event, we can't receive a unicast response for some reason
    
    This change puts ServiceInfo inline with ServiceBrowser which also
    asks the first question as QU since ServiceInfo is commonly called
    from ServiceBrowser callbacks

  - Limited duplicate packet suppression to 1s intervals (\#841) @bdraco
    
    Only suppress duplicate packets that happen within the same second.
    Legitimate queriers will retry the question if they are suppressed.
    The limit was reduced to one second to be in line with rfc6762

  - Made multipacket known answer suppression per interface (\#836)
    @bdraco
    
    The suppression was happening per instance of Zeroconf instead of
    per interface. Since the same network can be seen on multiple
    interfaces (usually and wifi and ethernet), this would confuse the
    multi-packet known answer supression since it was not expecting to
    get the same data more than once

  - New ServiceBrowsers now request QU in the first outgoing when
    unspecified (\#812) @bdraco
    
    <https://datatracker.ietf.org/doc/html/rfc6762#section-5.4> When we
    start a ServiceBrowser and zeroconf has just started up, the known
    answer list will be small. By asking a QU question first, it is
    likely that we have a large known answer list by the time we ask the
    QM question a second later (current default which is likely too low
    but would be a breaking change to increase). This reduces the amount
    of traffic on the network, and has the secondary advantage that most
    responders will answer a QU question without the typical delay
    answering QM questions.

  - IPv6 link-local addresses are now qualified with scope\_id (\#343)
    @ibygrave
    
    When a service is advertised on an IPv6 address where the scope is
    link local, i.e. fe80::/64 (see RFC 4007) the resolved IPv6 address
    must be extended with the scope\_id that identifies through the "%"
    symbol the local interface to be used when routing to that address.
    A new API <span class="title-ref">parsed\_scoped\_addresses()</span>
    is provided to return qualified addresses to avoid breaking
    compatibility on the existing parsed\_addresses().

  - Network adapters that are disconnected are now skipped (\#327)
    @ZLJasonG

  - Fixed listeners missing initial packets if Engine starts too quickly
    (\#387) @bdraco
    
    When manually creating a zeroconf.Engine object, it is no longer
    started automatically. It must manually be started by calling
    .start() on the created object.
    
    The Engine thread is now started after all the listeners have been
    added to avoid a race condition where packets could be missed at
    startup.

  - Fixed answering matching PTR queries with the ANY query (\#618)
    @bdraco

  - Fixed lookup of uppercase names in the registry (\#597) @bdraco
    
    If the ServiceInfo was registered with an uppercase name and the
    query was for a lowercase name, it would not be found and
    vice-versa.

  - Fixed unicast responses from any source port (\#598) @bdraco
    
    Unicast responses were only being sent if the source port was 53,
    this prevented responses when testing with dig:
    
    > dig -p 5353 @224.0.0.251 media-12.local
    
    The above query will now see a response

  - Fixed queries for AAAA records not being answered (\#616) @bdraco

  - Removed second level caching from ServiceBrowsers (\#737) @bdraco
    
    The ServiceBrowser had its own cache of the last time it saw a
    service that was reimplementing the DNSCache and presenting a source
    of truth problem that lead to unexpected queries when the two
    disagreed.

  - Fixed server cache not being case-insensitive (\#731) @bdraco
    
    If the server name had uppercase chars and any of the matching
    records were lowercase, and the server would not be found

  - Fixed cache handling of records with different TTLs (\#729) @bdraco
    
    There should only be one unique record in the cache at a time as
    having multiple unique records will different TTLs in the cache can
    result in unexpected behavior since some functions returned all
    matching records and some fetched from the right side of the list to
    return the newest record. Instead we now store the records in a dict
    to ensure that the newest record always replaces the same unique
    record, and we never have a source of truth problem determining the
    TTL of a record from the cache.

  - Fixed ServiceInfo with multiple A records (\#725) @bdraco
    
    If there were multiple A records for the host, ServiceInfo would
    always return the last one that was in the incoming packet, which
    was usually not the one that was wanted.

  - Fixed stale unique records expiring too quickly (\#706) @bdraco
    
    Records now expire 1s in the future instead of instant removal.
    
    tools.ietf.org/html/rfc6762\#section-10.2 Queriers receiving a
    Multicast DNS response with a TTL of zero SHOULD NOT immediately
    delete the record from the cache, but instead record a TTL of 1 and
    then delete the record one second later. In the case of multiple
    Multicast DNS responders on the network described in Section 6.6
    above, if one of the responders shuts down and incorrectly sends
    goodbye packets for its records, it gives the other cooperating
    responders one second to send out their own response to "rescue" the
    records before they expire and are deleted.

  - Fixed exception when unregistering a service multiple times (\#679)
    @bdraco

  - Added an AsyncZeroconfServiceTypes to mirror ZeroconfServiceTypes to
    zeroconf.asyncio (\#658) @bdraco

  - Fixed interface\_index\_to\_ip6\_address not skiping ipv4 adapters
    (\#651) @bdraco

  - Added async\_unregister\_all\_services to AsyncZeroconf (\#649)
    @bdraco

  - Fixed services not being removed from the registry when calling
    unregister\_all\_services (\#644) @bdraco
    
    There was a race condition where a query could be answered for a
    service in the registry, while goodbye packets which could result in
    a fresh record being broadcast after the goodbye if a query came in
    at just the right time. To avoid this, we now remove the services
    from the registry right after we generate the goodbye packet

  - Fixed zeroconf exception on load when the system disables IPv6
    (\#624) @bdraco

  - Fixed the QU bit missing from for probe queries (\#609) @bdraco
    
    The bit should be set per
    datatracker.ietf.org/doc/html/rfc6762\#section-8.1

  - Fixed the TC bit missing for query packets where the known answers
    span multiple packets (\#494) @bdraco

  - Fixed packets not being properly separated when exceeding maximum
    size (\#498) @bdraco
    
    Ensure that questions that exceed the max packet size are moved to
    the next packet. This fixes DNSQuestions being sent in multiple
    packets in violation of:
    datatracker.ietf.org/doc/html/rfc6762\#section-7.2
    
    Ensure only one resource record is sent when a record exceeds
    \_MAX\_MSG\_TYPICAL
    datatracker.ietf.org/doc/html/rfc6762\#section-17

  - Fixed PTR questions asked in uppercase not being answered (\#465)
    @bdraco

  - Added Support for context managers in Zeroconf and AsyncZeroconf
    (\#284) @shenek

  - Implemented an AsyncServiceBrowser to compliment the sync
    ServiceBrowser (\#429) @bdraco

  - Added async\_get\_service\_info to AsyncZeroconf and async\_request
    to AsyncServiceInfo (\#408) @bdraco

  - Implemented allowing passing in a sync Zeroconf instance to
    AsyncZeroconf (\#406) @bdraco

  - Fixed IPv6 setup under MacOS when binding to "" (\#392) @bdraco

  - Fixed ZeroconfServiceTypes.find not always cancels the
    ServiceBrowser (\#389) @bdraco
    
    There was a short window where the ServiceBrowser thread could be
    left running after Zeroconf is closed because the .join() was never
    waited for when a new Zeroconf object was created

  - Fixed duplicate packets triggering duplicate updates (\#376) @bdraco
    
    If TXT or SRV records update was already processed and then received
    again, it was possible for a second update to be called back in the
    ServiceBrowser

  - Fixed ServiceStateChange.Updated event happening for IPs that
    already existed (\#375) @bdraco

  - Fixed RFC6762 Section 10.2 paragraph 2 compliance (\#374) @bdraco

  - Reduced length of ServiceBrowser thread name with many types (\#373)
    @bdraco

  - Fixed empty answers being added in ServiceInfo.request (\#367)
    @bdraco

  - Fixed ServiceInfo not populating all AAAA records (\#366) @bdraco
    
    Use get\_all\_by\_details to ensure all records are loaded into
    addresses.
    
    Only load A/AAAA records from the cache once in load\_from\_cache if
    there is a SRV record present
    
    Move duplicate code that checked if the ServiceInfo was complete
    into its own function

  - Fixed a case where the cache list can change during iteration
    (\#363) @bdraco

  - Return task objects created by AsyncZeroconf (\#360) @nocarryr

Traffic Reduction:

  - Added support for handling QU questions (\#621) @bdraco
    
    Implements RFC 6762 sec 5.4: Questions Requesting Unicast Responses
    datatracker.ietf.org/doc/html/rfc6762\#section-5.4

  - Implemented protect the network against excessive packet flooding
    (\#619) @bdraco

  - Additionals are now suppressed when they are already in the answers
    section (\#617) @bdraco

  - Additionals are no longer included when the answer is suppressed by
    known-answer suppression (\#614) @bdraco

  - Implemented multi-packet known answer supression (\#687) @bdraco
    
    Implements datatracker.ietf.org/doc/html/rfc6762\#section-7.2

  - Implemented efficient bucketing of queries with known answers
    (\#698) @bdraco

  - Implemented duplicate question suppression (\#770) @bdraco
    
    <http://datatracker.ietf.org/doc/html/rfc6762#section-7.3>

Technically backwards incompatible:

  - Update internal version check to match docs (3.6+) (\#491) @bdraco
    
    Python version earlier then 3.6 were likely broken with zeroconf
    already, however, the version is now explicitly checked.

  - Update python compatibility as PyPy3 7.2 is required (\#523) @bdraco

Backwards incompatible:

  - Drop oversize packets before processing them (\#826) @bdraco
    
    Oversized packets can quickly overwhelm the system and deny service
    to legitimate queriers. In practice, this is usually due to broken
    mDNS implementations rather than malicious actors.

  - Guard against excessive ServiceBrowser queries from PTR records
    significantly lowerthan recommended (\#824) @bdraco
    
    We now enforce a minimum TTL for PTR records to avoid
    ServiceBrowsers generating excessive queries refresh queries. Apple
    uses a 15s minimum TTL, however, we do not have the same level of
    rate limit and safeguards, so we use 1/4 of the recommended value.

  - RecordUpdateListener now uses async\_update\_records instead of
    update\_record (\#419, \#726) @bdraco
    
    This allows the listener to receive all the records that have been
    updated in a single transaction such as a packet or cache expiry.
    
    update\_record has been deprecated in favor of
    async\_update\_records A compatibility shim exists to ensure classes
    that use RecordUpdateListener as a base class continue to have
    update\_record called, however, they should be updated as soon as
    possible.
    
    A new method async\_update\_records\_complete is now called on each
    listener when all listeners have completed processing updates and
    the cache has been updated. This allows ServiceBrowsers to delay
    calling handlers until they are sure the cache has been updated as
    its a common pattern to call for ServiceInfo when a ServiceBrowser
    handler fires.
    
    The async\_ prefix was chosen to make it clear that these functions
    run in the eventloop and should never do blocking I/O. Before 0.32+
    these functions ran in a select() loop and should not have been
    doing any blocking I/O, but it was not clear to implementors that
    I/O would block the loop.

  - Pass both the new and old records to async\_update\_records (\#792)
    @bdraco
    
    Pass the old\_record (cached) as the value and the new\_record
    (wire) to async\_update\_records instead of forcing each consumer to
    check the cache since we will always have the old\_record when
    generating the async\_update\_records call. This avoids the overhead
    of multiple cache lookups for each listener.

# 0.31.0

  - Separated cache loading from I/O in ServiceInfo and fixed cache
    lookup (\#356), thanks to J. Nick Koston.
    
    The ServiceInfo class gained a load\_from\_cache() method to only
    fetch information from Zeroconf cache (if it exists) with no IO
    performed. Additionally this should reduce IO in cases where cache
    lookups were previously incorrectly failing.

# 0.30.0

  - Some nice refactoring work including removal of the Reaper thread,
    thanks to J. Nick Koston.
  - Fixed a Windows-specific The requested address is not valid in its
    context regression, thanks to Timothee ‘TTimo’ Besset and J. Nick
    Koston.
  - Provided an asyncio-compatible service registration layer (in the
    zeroconf.asyncio module), thanks to J. Nick Koston.

# 0.29.0

  - A single socket is used for listening on responding when
    <span class="title-ref">InterfaceChoice.Default</span> is chosen.
    Thanks to J. Nick Koston.

Backwards incompatible:

  - Dropped Python 3.5 support

# 0.28.8

  - Fixed the packet generation when multiple packets are necessary,
    previously invalid packets were generated sometimes. Patch thanks to
    J. Nick Koston.

# 0.28.7

  - Fixed the IPv6 address rendering in the browser example, thanks to
    Alexey Vazhnov.
  - Fixed a crash happening when a service is added or removed during
    handle\_response and improved exception handling, thanks to J. Nick
    Koston.

# 0.28.6

  - Loosened service name validation when receiving from the network
    this lets us handle some real world devices previously causing
    errors, thanks to J. Nick Koston.

# 0.28.5

  - Enabled ignoring duplicated messages which decreases CPU usage,
    thanks to J. Nick Koston.
  - Fixed spurious AttributeError: module 'unittest' has no attribute
    'mock' in tests.

# 0.28.4

  - Improved cache reaper performance significantly, thanks to J. Nick
    Koston.
  - Added ServiceListener to \_\_all\_\_ as it's part of the public API,
    thanks to Justin Nesselrotte.

# 0.28.3

  - Reduced a time an internal lock is held which should eliminate
    deadlocks in high-traffic networks, thanks to J. Nick Koston.

# 0.28.2

  - Stopped asking questions we already have answers for in cache,
    thanks to Paul Daumlechner.
  - Removed initial delay before querying for service info, thanks to
    Erik Montnemery.

# 0.28.1

  - Fixed a resource leak connected to using ServiceBrowser with
    multiple types, thanks to
    10. Nick Koston.

# 0.28.0

  - Improved Windows support when using socket errno checks, thanks to
    Sandy Patterson.
  - Added support for passing text addresses to ServiceInfo.
  - Improved logging (includes fixing an incorrect logging call)
  - Improved Windows compatibility by using Adapter.index from ifaddr,
    thanks to PhilippSelenium.
  - Improved Windows compatibility by stopping using
    socket.if\_nameindex.
  - Fixed an OS X edge case which should also eliminate a memory leak,
    thanks to Emil Styrke.

Technically backwards incompatible:

  - `ifaddr` 0.1.7 or newer is required now.

## 0.27.1

  - Improved the logging situation (includes fixing a false-positive
    "packets() made no progress adding records", thanks to Greg Badros)

## 0.27.0

  - Large multi-resource responses are now split into separate packets
    which fixes a bad mdns-repeater/ChromeCast Audio interaction ending
    with ChromeCast Audio crash (and possibly some others) and improves
    RFC 6762 compliance, thanks to Greg Badros
  - Added a warning presented when the listener passed to ServiceBrowser
    lacks update\_service() callback
  - Added support for finding all services available in the browser
    example, thanks to Perry Kunder

Backwards incompatible:

  - Removed previously deprecated ServiceInfo address constructor
    parameter and property

## 0.26.3

  - Improved readability of logged incoming data, thanks to Erik
    Montnemery
  - Threads are given unique names now to aid debugging, thanks to Erik
    Montnemery
  - Fixed a regression where get\_service\_info() called within a
    listener add\_service method would deadlock, timeout and incorrectly
    return None, fix thanks to Erik Montnemery, but Matt Saxon and
    Hmmbob were also involved in debugging it.

## 0.26.2

  - Added support for multiple types to ServiceBrowser, thanks to J.
    Nick Koston
  - Fixed a race condition where a listener gets a message before the
    lock is created, thanks to
    10. Nick Koston

## 0.26.1

  - Fixed a performance regression introduced in 0.26.0, thanks to J.
    Nick Koston (this is close in spirit to an optimization made in
    0.24.5 by the same author)

## 0.26.0

  - Fixed a regression where service update listener wasn't called on IP
    address change (it's called on SRV/A/AAAA record changes now),
    thanks to Matt Saxon

Technically backwards incompatible:

  - Service update hook is no longer called on service addition (service
    added hook is still called), this is related to the fix above

## 0.25.1

  - Eliminated 5s hangup when calling Zeroconf.close(), thanks to Erik
    Montnemery

## 0.25.0

  - Reverted uniqueness assertions when browsing, they caused a
    regression

Backwards incompatible:

  - Rationalized handling of TXT records. Non-bytes values are converted
    to str and encoded to bytes using UTF-8 now, None values mean
    value-less attributes. When receiving TXT records no decoding is
    performed now, keys are always bytes and values are either bytes or
    None in value-less attributes.

## 0.24.5

  - Fixed issues with shared records being used where they shouldn't be
    (TXT, SRV, A records are unique now), thanks to Matt Saxon
  - Stopped unnecessarily excluding host-only interfaces from
    InterfaceChoice.all as they don't forbid multicast, thanks to
    Andreas Oberritter
  - Fixed repr() of IPv6 DNSAddress, thanks to Aldo Hoeben
  - Removed duplicate update messages sent to listeners, thanks to Matt
    Saxon
  - Added support for cooperating responders, thanks to Matt Saxon
  - Optimized handle\_response cache check, thanks to J. Nick Koston
  - Fixed memory leak in DNSCache, thanks to J. Nick Koston

## 0.24.4

  - Fixed resetting TTL in DNSRecord.reset\_ttl(), thanks to Matt Saxon
  - Improved various DNS class' string representations, thanks to Jay
    Hogg

## 0.24.3

  - Fixed import-time "TypeError: 'ellipsis' object is not iterable." on
    CPython 3.5.2

## 0.24.2

  - Added support for AWDL interface on macOS (needed and used by the
    opendrop project but should be useful in general), thanks to Milan
    Stute
  - Added missing type hints

## 0.24.1

  - Applied some significant performance optimizations, thanks to Jaime
    van Kessel for the patch and to Ghostkeeper for performance
    measurements
  - Fixed flushing outdated cache entries when incoming record is
    unique, thanks to Michael Hu
  - Fixed handling updates of TXT records (they'd not get recorded
    previously), thanks to Michael Hu

## 0.24.0

  - Added IPv6 support, thanks to Dmitry Tantsur
  - Added additional recommended records to PTR responses, thanks to
    Scott Mertz
  - Added handling of ENOTCONN being raised during shutdown when using
    Eventlet, thanks to Tamás Nepusz
  - Included the py.typed marker in the package so that type checkers
    know to use type hints from the source code, thanks to Dmitry
    Tantsur

## 0.23.0

  - Added support for MyListener call getting updates to service TXT
    records, thanks to Matt Saxon
  - Added support for multiple addresses when publishing a service,
    getting/setting single address has become deprecated. Change thanks
    to Dmitry Tantsur

Backwards incompatible:

  - Dropped Python 3.4 support

## 0.22.0

  - A lot of maintenance work (tooling, typing coverage and
    improvements, spelling) done, thanks to Ville Skyttä
  - Provided saner defaults in ServiceInfo's constructor, thanks to
    Jorge Miranda
  - Fixed service removal packets not being sent on shutdown, thanks to
    Andrew Bonney
  - Added a way to define TTL-s through ServiceInfo contructor
    parameters, thanks to Andrew Bonney

Technically backwards incompatible:

  - Adjusted query intervals to match RFC 6762, thanks to Andrew Bonney
  - Made default TTL-s match RFC 6762, thanks to Andrew Bonney

## 0.21.3

  - This time really allowed incoming service names to contain
    underscores (patch released as part of 0.21.0 was defective)

## 0.21.2

  - Fixed import-time typing-related TypeError when older typing version
    is used

## 0.21.1

  - Fixed installation on Python 3.4 (we use typing now but there was no
    explicit dependency on it)

## 0.21.0

  - Added an error message when importing the package using unsupported
    Python version
  - Fixed TTL handling for published service
  - Implemented unicast support
  - Fixed WSL (Windows Subsystem for Linux) compatibility
  - Fixed occasional UnboundLocalError issue
  - Fixed UTF-8 multibyte name compression
  - Switched from netifaces to ifaddr (pure Python)
  - Allowed incoming service names to contain underscores

## 0.20.0

  - Dropped support for Python 2 (this includes PyPy) and 3.3
  - Fixed some class' equality operators
  - ServiceBrowser entries are being refreshed when 'stale' now
  - Cache returns new records first now instead of last

## 0.19.1

  - Allowed installation with netifaces \>= 0.10.6 (a bug that was
    concerning us got fixed)

## 0.19.0

  - Technically backwards incompatible - restricted netifaces dependency
    version to work around a bug, see
    <https://github.com/jstasiak/python-zeroconf/issues/84> for details

## 0.18.0

  - Dropped Python 2.6 support
  - Improved error handling inside code executed when Zeroconf object is
    being closed

## 0.17.7

  - Better Handling of DNS Incoming Packets parsing exceptions
  - Many exceptions will now log a warning the first time they are seen
  - Catch and log sendto() errors
  - Fix/Implement duplicate name change
  - Fix overly strict name validation introduced in 0.17.6
  - Greatly improve handling of oversized packets including:
      - Implement name compression per RFC1035
      - Limit size of generated packets to 9000 bytes as per RFC6762
      - Better handle over sized incoming packets
  - Increased test coverage to 95%

## 0.17.6

  - Many improvements to address race conditions and exceptions during
    ZC() startup and shutdown, thanks to: morpav, veawor, justingiorgi,
    herczy, stephenrauch
  - Added more test coverage: strahlex, stephenrauch
  - Stephen Rauch contributed:
      - Speed up browser startup
      - Add ZeroconfServiceTypes() query class to discover all
        advertised service types
      - Add full validation for service names, types and subtypes
      - Fix for subtype browsing
      - Fix DNSHInfo support

## 0.17.5

  - Fixed OpenBSD compatibility, thanks to Alessio Sergi
  - Fixed race condition on ServiceBrowser startup, thanks to gbiddison
  - Fixed installation on some Python 3 systems, thanks to Per Sandström
  - Fixed "size change during iteration" bug on Python 3, thanks to
    gbiddison

## 0.17.4

  - Fixed support for Linux kernel versions \< 3.9 (thanks to Giovanni
    Harting and Luckydonald, GitHub pull request \#26)

## 0.17.3

  - Fixed DNSText repr on Python 3 (it'd crash when the text was longer
    than 10 bytes), thanks to Paulus Schoutsen for the patch, GitHub
    pull request \#24

## 0.17.2

  - Fixed installation on Python 3.4.3+ (was failing because of enum34
    dependency which fails to install on 3.4.3+, changed to depend on
    enum-compat instead; thanks to Michael Brennan for the original
    patch, GitHub pull request \#22)

## 0.17.1

  - Fixed EADDRNOTAVAIL when attempting to use dummy network interfaces
    on Windows, thanks to daid

## 0.17.0

  - Added some Python dependencies so it's not zero-dependencies anymore
  - Improved exception handling (it'll be quieter now)
  - Messages are listened to and sent using all available network
    interfaces by default (configurable); thanks to Marcus Müller
  - Started using logging more freely
  - Fixed a bug with binary strings as property values being converted
    to False (<https://github.com/jstasiak/python-zeroconf/pull/10>);
    thanks to Dr. Seuss
  - Added new `ServiceBrowser` event handler interface (see the
    examples)
  - PyPy3 now officially supported
  - Fixed ServiceInfo repr on Python 3, thanks to Yordan Miladinov

## 0.16.0

  - Set up Python logging and started using it
  - Cleaned up code style (includes migrating from camel case to snake
    case)

## 0.15.1

  - Fixed handling closed socket (GitHub \#4)

## 0.15

  - Forked by Jakub Stasiak
  - Made Python 3 compatible
  - Added setup script, made installable by pip and uploaded to PyPI
  - Set up Travis build
  - Reformatted the code and moved files around
  - Stopped catching BaseException in several places, that could hide
    errors
  - Marked threads as daemonic, they won't keep application alive now

## 0.14

  - Fix for SOL\_IP undefined on some systems - thanks Mike Erdely.
  - Cleaned up examples.
  - Lowercased module name.

## 0.13

  - Various minor changes; see git for details.
  - No longer compatible with Python 2.2. Only tested with 2.5-2.7.
  - Fork by William McBrine.

## 0.12

  - allow selection of binding interface
  - typo fix - Thanks A. M. Kuchlingi
  - removed all use of word 'Rendezvous' - this is an API change

## 0.11

  - correction to comments for addListener method
  - support for new record types seen from OS X
      - IPv6 address
      - hostinfo
  - ignore unknown DNS record types
  - fixes to name decoding
  - works alongside other processes using port 5353 (e.g. on Mac OS X)
  - tested against Mac OS X 10.3.2's mDNSResponder
  - corrections to removal of list entries for service browser

## 0.10

  - Jonathon Paisley contributed these corrections:
      - always multicast replies, even when query is unicast
      - correct a pointer encoding problem
      - can now write records in any order
      - traceback shown on failure
      - better TXT record parsing
      - server is now separate from name
      - can cancel a service browser
  - modified some unit tests to accommodate these changes

## 0.09

  - remove all records on service unregistration
  - fix DOS security problem with readName

## 0.08

  - changed licensing to LGPL

## 0.07

  - faster shutdown on engine
  - pointer encoding of outgoing names
  - ServiceBrowser now works
  - new unit tests

## 0.06

  - small improvements with unit tests
  - added defined exception types
  - new style objects
  - fixed hostname/interface problem
  - fixed socket timeout problem
  - fixed add\_service\_listener() typo bug
  - using select() for socket reads
  - tested on Debian unstable with Python 2.2.2

## 0.05

  - ensure case insensitivty on domain names
  - support for unicast DNS queries

## 0.04

  - added some unit tests
  - added \_\_ne\_\_ adjuncts where required
  - ensure names end in '.local.'
  - timeout on receiving socket for clean shutdown
