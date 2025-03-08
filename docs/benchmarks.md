# Benchmarks

-----

## Setup

Download [Hatch](https://hatch.pypa.io/latest/install/) or [UV](https://docs.astral.sh/uv/getting-started/installation/) in order to run the benchmarks as follows:

```
[hatch|uv] run scripts/bench.py
```

## Results

| Library | Key generation | Signing | Verification | Key export | Key import |
| --- | --- | --- | --- | --- | --- |
| coincurve v21.0.0 | 33.4 | 52.8 | 59.0 | 12.6 | 39.4 |
| [fastecdsa](https://github.com/AntonKueltz/fastecdsa) v3.0.1 | 1319.6 | 1449.5 | 1160.4 | 1402.9 | 15.5 |

!!! note
    - the timings are in microseconds
    - signing and verification use a 16 KiB message
    - the Python version used for the benchmarks is 3.13.x
