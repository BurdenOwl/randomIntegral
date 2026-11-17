import argparse
import json
import math
import random
import subprocess
import sys
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import sympy as sp
from sympy.integrals.risch import risch_integrate

from generator import expression_to_latex, generate_expression


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ADDRESS = ("127.0.0.1", 8000)
SERVER_VERSION = str(time.time_ns())
ALLOWED_ORIGINS = {"http://localhost:5500", "http://127.0.0.1:5500"}


def python_files_snapshot() -> dict[Path, tuple[int, int]]:
    snapshot = {}
    for path in (PROJECT_ROOT / "ui").rglob("*.py"):
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        snapshot[path] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def run_with_reload() -> None:
    watched_files = python_files_snapshot()
    child = subprocess.Popen([sys.executable, str(Path(__file__).resolve())], cwd=PROJECT_ROOT)
    print("Watching ui/*.py for changes. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(0.5)
            current_files = python_files_snapshot()
            if current_files != watched_files:
                watched_files = current_files
                print("Python changes detected; restarting the web server.")
                child.terminate()
                child.wait()
                child = subprocess.Popen(
                    [sys.executable, str(Path(__file__).resolve())],
                    cwd=PROJECT_ROOT,
                )
            elif child.poll() is not None:
                print(f"Web server exited with status {child.returncode}; restarting.")
                child = subprocess.Popen(
                    [sys.executable, str(Path(__file__).resolve())],
                    cwd=PROJECT_ROOT,
                )
    except KeyboardInterrupt:
        print("Stopping web server.")
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


def sample_expression(
    expression: sp.Expr,
    variable: sp.Symbol,
    x_values: list[float],
) -> list[Optional[float]]:
    samples = []
    for x_value in x_values:
        try:
            value = complex(expression.subs(variable, x_value).evalf())
            if (
                not math.isfinite(value.real)
                or not math.isfinite(value.imag)
                or abs(value.imag) > 1e-10 * max(1.0, abs(value.real))
            ):
                samples.append(None)
            else:
                samples.append(value.real)
        except (ArithmeticError, TypeError, ValueError, NotImplementedError):
            samples.append(None)
    return samples


class IntegralRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def send_api_headers(self, response: bytes) -> None:
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Cache-Control", "no-store")
        origin = self.headers.get("Origin")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/version":
            response = json.dumps({"version": SERVER_VERSION}).encode("utf-8")
            self.send_response(200)
            self.send_api_headers(response)
            self.wfile.write(response)
            return

        if path != "/api/integral":
            return super().do_GET()

        expression = generate_expression()
        variable = sp.Symbol("x")
        if random.random() < 0.5:
            expression /= variable + random.randint(1, 5)
        derivative = sp.diff(expression, variable)
        try:
            risch = risch_integrate(expression, variable, rewrite_complex=True)
            risch_latex = expression_to_latex(risch)
            risch_error = None
        except NotImplementedError:
            risch = None
            risch_latex = None
            risch_error = "The Risch algorithm does not support this expression."
        try:
            sympy_integral = sp.integrate(derivative, variable)
            sympy_integral_latex = expression_to_latex(sympy_integral)
            sympy_integral_error = None
        except NotImplementedError:
            sympy_integral = None
            sympy_integral_latex = None
            sympy_integral_error = "SymPy could not find a closed-form integral."
        x_values = [-10 + index * 0.1 for index in range(201)]
        expression_values = sample_expression(expression, variable, x_values)
        risch_values = (
            sample_expression(risch, variable, x_values) if risch is not None else None
        )
        sympy_integral_values = (
            sample_expression(sympy_integral, variable, x_values)
            if sympy_integral is not None
            else None
        )
        if risch_values is not None and all(value is None for value in risch_values):
            risch_values = None
        if sympy_integral_values is not None and all(
            value is None for value in sympy_integral_values
        ):
            sympy_integral_values = None
        response = json.dumps(
            {
                "expression_latex": expression_to_latex(expression),
                "derivative_latex": expression_to_latex(derivative),
                "risch_latex": risch_latex,
                "risch_error": risch_error,
                "symIntegral_latex": sympy_integral_latex,
                "symIntegral_error": sympy_integral_error,
                "x_values": x_values,
                "expression_values": expression_values,
                "risch_values": risch_values,
                "symIntegral_values": sympy_integral_values,
                "server_version": SERVER_VERSION,
            }
        ).encode("utf-8")

        self.send_response(200)
        self.send_api_headers(response)
        self.wfile.write(response)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reload",
        action="store_true",
        help="restart the server when Python files in ui/ change",
    )
    args = parser.parse_args()

    if args.reload:
        run_with_reload()
    else:
        print(f"Open http://{ADDRESS[0]}:{ADDRESS[1]} in your browser")
        try:
            ThreadingHTTPServer(ADDRESS, IntegralRequestHandler).serve_forever()
        except OSError as error:
            raise SystemExit(
                f"Could not start server on http://{ADDRESS[0]}:{ADDRESS[1]}: {error}. "
                "Close the process already using port 8000 and try again."
            ) from error
