# C01 declarations

`protocol.json` freezes the one development batch, source selection and admission
rule before any C01 inference. Local immutable build plans and snapshots are under
`data/indexes/c01`; mutable progress and the cumulative ledger are under
`data/runs/indexing`. None of these opens an earlier stage's allowance.
