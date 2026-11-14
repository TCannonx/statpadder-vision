# Score m01 (degraded)

| group | truth | predicted | matched | recall 2s | precision 2s | recall 5s | precision 5s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| goal | 2 | 2 | 2 | 0% | 0% | 100% | 100% |
| corner | 10 | 8 | 8 | 0% | 0% | 80% | 100% |
| free_kick_final_third | 7 | 4 | 4 | 0% | 0% | 57% | 100% |
| shot | 16 | 15 | 9 | 12% | 13% | 56% | 60% |

Accuracy at 5s: team 23/23 (100%), zone 22/23 (95%). Team mapping: by name.
halves scored: 1, 2

## Bar (at 5s)

| test | value | need | result |
| --- | --- | --- | --- |
| goal recall | 100% | 90% | PASS |
| corner recall | 80% | 75% | PASS |
| corner precision | 100% | 70% | PASS |
| free_kick_final_third recall | 57% | 75% | FAIL |
| free_kick_final_third precision | 100% | 70% | PASS |
| shot recall | 56% | 75% | FAIL |
| shot precision | 60% | 70% | FAIL |
| team | 100% | 90% | PASS |
| zone | 95% | 70% | PASS |
