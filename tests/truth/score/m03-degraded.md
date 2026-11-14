# Score m03 (degraded)

| group | truth | predicted | matched | recall 2s | precision 2s | recall 5s | precision 5s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| goal | 2 | 2 | 2 | 0% | 0% | 100% | 100% |
| corner | 13 | 9 | 9 | 0% | 0% | 69% | 100% |
| free_kick_final_third | 5 | 5 | 5 | 0% | 0% | 100% | 100% |
| shot | 20 | 19 | 14 | 0% | 0% | 70% | 74% |

Accuracy at 5s: team 30/30 (100%), zone 30/30 (100%). Team mapping: by name.

## Bar (at 5s)

| test | value | need | result |
| --- | --- | --- | --- |
| goal recall | 100% | 90% | PASS |
| corner recall | 69% | 75% | FAIL |
| corner precision | 100% | 70% | PASS |
| free_kick_final_third recall | 100% | 75% | PASS |
| free_kick_final_third precision | 100% | 70% | PASS |
| shot recall | 70% | 75% | FAIL |
| shot precision | 74% | 70% | PASS |
| team | 100% | 90% | PASS |
| zone | 100% | 70% | PASS |
