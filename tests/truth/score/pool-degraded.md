# Score pool (degraded)

| group | truth | predicted | matched | recall 2s | precision 2s | recall 5s | precision 5s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| goal | 4 | 4 | 4 | 0% | 0% | 100% | 100% |
| corner | 23 | 17 | 17 | 0% | 0% | 74% | 100% |
| free_kick_final_third | 12 | 9 | 9 | 0% | 0% | 75% | 100% |
| shot | 36 | 34 | 23 | 6% | 6% | 64% | 68% |

Accuracy at 5s: team 53/53 (100%), zone 52/53 (98%). Team mapping: by name.

## Bar (at 5s)

| test | value | need | result |
| --- | --- | --- | --- |
| goal recall | 100% | 90% | PASS |
| corner recall | 74% | 75% | FAIL |
| corner precision | 100% | 70% | PASS |
| free_kick_final_third recall | 75% | 75% | PASS |
| free_kick_final_third precision | 100% | 70% | PASS |
| shot recall | 64% | 75% | FAIL |
| shot precision | 68% | 70% | FAIL |
| team | 100% | 90% | PASS |
| zone | 98% | 70% | PASS |
