---
title: "Ticket 022 - Verification gate"
date: 2026-10-21
type: task
status: open
where: docs/wayfinder/tickets/022-verification-gate.md
---

# Ticket 022: Verification gate

Triple check over tickets 019 to 021:

1. Verifier with hand-typed expected values for every headline figure.
2. Byte-identical rerun from scratch.
3. Independent second derivation of every published number (separate
   implementation, same inputs).
4. The finished split loaded through a row loader that is not the builder's.
5. If the VM is used at all (read-only): md5 pairs on both machines for every
   compared artifact, nothing written to the VM tree.

Done when every check passes and the failures-on-corrupted-input proof is
shown for the verifier.

## Progress 2026-10-23

Split legs DONE: byte-identical rerun of build_split.py (md5 match on
split.csv and meta.json), hand-typed expected values for every per-class
split count (verify_split.py, all pass), independent second derivation with
set logic (all pass), coverage via a loader that is not the builder's, and
the failures-on-corrupted-input proof (5 moved rows caught, exit 1).

STILL OPEN: the picture-by-picture checks of the parked items from the
2026-10-21 session: Fiber gate 137-vs-136, Folded Lens 237-vs-178, the
84-picture rescue set. Nothing else blocks the experiment from starting.
