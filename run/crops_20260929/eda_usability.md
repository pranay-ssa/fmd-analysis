# Single-size usability EDA (canonical windows, 120px margin embedded)

## Updated ICube Categorical Classes 20260915

| class | n | ok | expanded | tier2 | tier3 | max need WxH | canonical | verdict |
|---|---|---|---|---|---|---|---|---|
| Bubble Scatter | 6 | 6 | 0 | 0 | 0 | 1395x1365 | 1548x1516 | USABLE as-is |
| Cavity Off Center | 183 | 167 | 0 | 19 | 16 | 1567x1414 | 1704x1564 | USABLE as-is |
| Dirty Camera | 25 | 25 | 0 | 0 | 0 | 1730x1564 | 1876x1716 | USABLE as-is |
| Dirty Strobe | 42 | 42 | 0 | 0 | 0 | 1419x1669 | 1572x1788 | USABLE as-is |
| HEMA Obstruction | 175 | 175 | 0 | 0 | 0 | 1495x1492 | 1584x1532 | USABLE as-is |
| Lens Off Center | 258 | 252 | 6 | 0 | 0 | 1671x1497 | 1580x1560 | usable, 6 no-loss-guard images (6/258) |
| Low Dose | 1952 | 1935 | 17 | 0 | 0 | 1662x1742 | 1548x1528 | usable, 17 no-loss-guard images (17/1952) |
| Missing Lens | 324 | 268 | 56 | 0 | 0 | 1688x1791 | 1544x1524 | PROBLEM: 56/324 would trigger no-loss guard |
| Missing Primary Package | 1427 | 1404 | 23 | 0 | 0 | 1777x1725 | 1520x1516 | usable, 23 no-loss-guard images (23/1427) |
| Multiple Lenses | 1439 | 1424 | 15 | 0 | 0 | 1724x1689 | 1592x1592 | usable, 15 no-loss-guard images (15/1439) |
| Package Misalignment | 293 | 292 | 1 | 1 | 0 | 1993x2098 | 2020x2048 | usable, 1 no-loss-guard images (1/293) |
| View Obstructed | 117 | 7 | 7 | 1 | 103 | 2017x2138 | 1496x1296 | PROBLEM: 7/117 would trigger no-loss guard |
| duplicates | 143 | 0 | 132 | 6 | 11 | 1732x1634 | - | no canonical (new class) - skip |

## Updated ICube Objects 20260915

| class | n | ok | expanded | tier2 | tier3 | max need WxH | canonical | verdict |
|---|---|---|---|---|---|---|---|---|
| Clear | 2333 | 0 | 2333 | 0 | 0 | 1677x1640 | - | no canonical (new class) - skip |
| Extraneous Polymer | 267 | 265 | 2 | 0 | 0 | 1788x1646 | 1576x1524 | usable, 2 no-loss-guard images (2/267) |
| Fiber | 328 | 325 | 3 | 0 | 0 | 1610x1633 | 1560x1528 | usable, 3 no-loss-guard images (3/328) |
| Foreign Matter | 1282 | 1270 | 12 | 0 | 0 | 1698x1665 | 1556x1784 | usable, 12 no-loss-guard images (12/1282) |
| HEMA | 20 | 20 | 0 | 0 | 0 | 1396x1378 | 1544x1520 | USABLE as-is |

## ICube Defects Library

| class | n | ok | expanded | tier2 | tier3 | max need WxH | canonical | verdict |
|---|---|---|---|---|---|---|---|---|
| Bubble | 114 | 114 | 0 | 0 | 0 | 1427x1385 | 1560x1532 | USABLE as-is |
| Bubble Cluster | 36 | 36 | 0 | 0 | 0 | 1443x1431 | 1596x1584 | USABLE as-is |
| Bubble Irregular | 44 | 44 | 0 | 0 | 0 | 1403x1372 | 1556x1524 | USABLE as-is |
| Bubble On 123 | 14 | 14 | 0 | 0 | 0 | 1390x1387 | 1540x1540 | USABLE as-is |
| Bubble On Edge | 14 | 14 | 0 | 0 | 0 | 1412x1414 | 1564x1564 | USABLE as-is |
| Bubble Scatter | 7 | 7 | 0 | 0 | 0 | 1395x1365 | 1548x1516 | USABLE as-is |
| Cavity Off Center | 98 | 93 | 0 | 12 | 5 | 1556x1414 | 1704x1564 | USABLE as-is |
| Dirty Camera | 25 | 25 | 0 | 0 | 0 | 1730x1564 | 1876x1716 | USABLE as-is |
| Dirty Strobe | 43 | 43 | 0 | 0 | 0 | 1419x1669 | 1572x1788 | USABLE as-is |
| Extraneous Polymer | 17 | 17 | 0 | 0 | 0 | 1423x1374 | 1576x1524 | USABLE as-is |
| Fiber | 61 | 61 | 0 | 0 | 0 | 1407x1378 | 1560x1528 | USABLE as-is |
| Foreign Matter | 71 | 71 | 0 | 0 | 0 | 1405x1665 | 1556x1784 | USABLE as-is |
| HEMA Fragment | 8 | 8 | 0 | 0 | 0 | 1393x1370 | 1544x1520 | USABLE as-is |
| HEMA Obstruction | 105 | 105 | 0 | 0 | 0 | 1434x1445 | 1584x1532 | USABLE as-is |
| Lens Off Center | 30 | 30 | 0 | 0 | 0 | 1430x1408 | 1580x1560 | USABLE as-is |
| Low Dose Obstructing Region of Interest | 93 | 93 | 0 | 0 | 0 | 1398x1375 | 1548x1528 | USABLE as-is |
| Missing Lens | 21 | 21 | 0 | 0 | 0 | 1393x1373 | 1544x1524 | USABLE as-is |
| Missing Primary Package | 315 | 314 | 1 | 0 | 0 | 1747x1548 | 1520x1516 | usable, 1 no-loss-guard images (1/315) |
| Multiple Lenses | 207 | 205 | 2 | 0 | 0 | 1638x1498 | 1592x1592 | usable, 2 no-loss-guard images (2/207) |
| Package Misalignment | 37 | 37 | 0 | 1 | 0 | 1869x2034 | 2020x2048 | USABLE as-is |
| View Obstructed | 22 | 6 | 0 | 0 | 16 | 1343x1143 | 1496x1296 | USABLE as-is |
| Wet Package | 83 | 83 | 0 | 0 | 0 | 1400x1390 | 1552x1540 | USABLE as-is |
