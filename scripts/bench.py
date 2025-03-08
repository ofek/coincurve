# /// script
# dependencies = [
#   "coincurve",
#   "fastecdsa==3.0.1; sys_platform != 'win32'",
#   "rich",
# ]
# [tool.uv.sources]
# coincurve = { path = ".." }
# ///
import os
import sys
from abc import ABC, abstractmethod
from decimal import Decimal
from textwrap import dedent
from time import perf_counter_ns
from timeit import Timer

from rich.live import Live
from rich.table import Table

MESSAGE = os.urandom(8192).hex()


class BenchmarkSpec:
    __slots__ = ("setup", "statement")

    def __init__(self, setup: str, statement: str):
        self.setup = dedent(setup[1:])
        self.statement = dedent(statement[1:])


class Benchmark(ABC):
    @staticmethod
    @abstractmethod
    def name() -> str:
        pass

    @staticmethod
    @abstractmethod
    def generate_key_pair() -> BenchmarkSpec:
        pass

    @staticmethod
    @abstractmethod
    def sign() -> BenchmarkSpec:
        pass

    @staticmethod
    @abstractmethod
    def verify() -> BenchmarkSpec:
        pass

    @staticmethod
    @abstractmethod
    def key_export() -> BenchmarkSpec:
        pass

    @staticmethod
    @abstractmethod
    def key_import() -> BenchmarkSpec:
        pass


class CoincurveBenchmark(Benchmark):
    @staticmethod
    def name() -> str:
        return "coincurve"

    @staticmethod
    def generate_key_pair() -> BenchmarkSpec:
        return BenchmarkSpec(
            """
            from coincurve import PrivateKey
            """,
            """
            PrivateKey()
            """,
        )

    @staticmethod
    def sign() -> BenchmarkSpec:
        return BenchmarkSpec(
            f"""
            from coincurve import PrivateKey
            message = {MESSAGE!r}.encode()
            private_key = PrivateKey()
            """,
            """
            private_key.sign(message)
            """,
        )

    @staticmethod
    def verify() -> BenchmarkSpec:
        return BenchmarkSpec(
            f"""
            from coincurve import PrivateKey, verify_signature
            message = {MESSAGE!r}.encode()
            private_key = PrivateKey()
            signature = private_key.sign(message)
            public_key = private_key.public_key.format(compressed=False)
            """,
            """
            assert verify_signature(signature, message, public_key)
            """,
        )

    @staticmethod
    def key_export() -> BenchmarkSpec:
        return BenchmarkSpec(
            """
            from coincurve import PrivateKey
            private_key = PrivateKey()
            """,
            """
            private_key.to_pem()
            """,
        )

    @staticmethod
    def key_import() -> BenchmarkSpec:
        return BenchmarkSpec(
            """
            from coincurve import PrivateKey
            private_key = PrivateKey()
            private_key_pem = private_key.to_pem()
            """,
            """
            PrivateKey.from_pem(private_key_pem)
            """,
        )


class FastecdsaBenchmark(Benchmark):
    @staticmethod
    def name() -> str:
        return "fastecdsa"

    @staticmethod
    def generate_key_pair() -> BenchmarkSpec:
        return BenchmarkSpec(
            """
            from fastecdsa import curve, keys
            """,
            """
            keys.gen_keypair(curve.secp256k1)
            """,
        )

    @staticmethod
    def sign() -> BenchmarkSpec:
        return BenchmarkSpec(
            f"""
            from fastecdsa import curve, ecdsa, keys
            message = {MESSAGE!r}
            private_key, _ = keys.gen_keypair(curve.secp256k1)
            """,
            """
            r, s = ecdsa.sign(message, private_key, curve=curve.secp256k1)
            """,
        )

    @staticmethod
    def verify() -> BenchmarkSpec:
        return BenchmarkSpec(
            f"""
            from fastecdsa import curve, ecdsa, keys
            message = {MESSAGE!r}
            private_key, public_key = keys.gen_keypair(curve.secp256k1)
            r, s = ecdsa.sign(message, private_key, curve=curve.secp256k1)
            """,
            """
            assert ecdsa.verify((r, s), message, public_key, curve=curve.secp256k1)
            """,
        )

    @staticmethod
    def key_export() -> BenchmarkSpec:
        return BenchmarkSpec(
            """
            from fastecdsa import curve, keys
            from fastecdsa.encoding.pem import PEMEncoder
            private_key, _ = keys.gen_keypair(curve.secp256k1)
            encoder = PEMEncoder()
            """,
            """
            encoder.encode_private_key(private_key, curve=curve.secp256k1)
            """,
        )

    @staticmethod
    def key_import() -> BenchmarkSpec:
        return BenchmarkSpec(
            """
            from fastecdsa import curve, keys
            from fastecdsa.encoding.pem import PEMEncoder
            private_key, _ = keys.gen_keypair(curve.secp256k1)
            encoder = PEMEncoder()
            private_key_pem = encoder.encode_private_key(private_key, curve=curve.secp256k1)
            """,
            """
            encoder.decode_private_key(private_key_pem)
            """,
        )


def generate_table(rows: list[list[str]]):
    table = Table()
    table.add_column("Library")
    table.add_column("Key generation")
    table.add_column("Signing")
    table.add_column("Verification")
    table.add_column("Key export")
    table.add_column("Key import")

    for row in rows:
        table.add_row(*row)

    return table


def main():
    print(sys.version)
    rows = []
    table = generate_table(rows)

    with Live(table, auto_refresh=False) as live:
        for benchmark in [CoincurveBenchmark, FastecdsaBenchmark]:
            row = [benchmark.name()]
            rows.append(row)
            live.update(generate_table(rows), refresh=True)

            for method in [
                benchmark.generate_key_pair,
                benchmark.sign,
                benchmark.verify,
                benchmark.key_export,
                benchmark.key_import,
            ]:
                spec = method()
                timer = Timer(stmt=spec.statement, setup=spec.setup, timer=perf_counter_ns)

                try:
                    loops, _ = timer.autorange()
                    times = timer.repeat(number=loops, repeat=1000)
                except Exception as e:  # noqa: BLE001
                    row.append(str(e))
                    live.update(generate_table(rows), refresh=True)
                    continue

                best = Decimal(min(times))
                # Convert nanoseconds to microseconds and round to 1 decimal place
                best /= 1_000
                best = best.quantize(Decimal("0.1"))

                row.append(str(best))
                live.update(generate_table(rows), refresh=True)


if __name__ == "__main__":
    main()
