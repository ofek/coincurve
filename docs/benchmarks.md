# Benchmarks

-----

The controlled benchmark workflow compares the handwritten extension with the CFFI implementation at commit `2d11b1160c75ae8fd94fe8fe3f226aec176bf9bf` on Linux x86-64 using CPython 3.10, 3.14, and free-threaded 3.14. Every result records the Python environment and the pinned libsecp256k1 commit in pyperf JSON.

Run the rewrite suite locally with:

```
uv run scripts/bench.py --output benchmark.json --rigorous
```

Binding overhead is measured with fixed 32-byte digests, while SHA-256 is measured separately. The suite covers fixed and random key construction, ECDSA signing and verification, recoverable signatures, Schnorr signatures, ECDH, parsing, serialization, tweaks, DER and PEM conversion, and sequence and packed batches at sizes 1, 16, 256, and 4096.

The release criteria are:

- No scalar hot operation may regress by more than 5% against the CFFI baseline on the controlled runner.
- Binding-dominated parsing, serialization, and tweak operations should improve by at least 20%.
- Digest batches of 256 or more items must deliver at least twice the throughput of equivalent scalar Python loops.

These thresholds are evaluated from retained benchmark artifacts before a release candidate is promoted. They are not timing assertions in ordinary CI.
