"""Thin MCP wrapper over phantom-training's existing tested capabilities.

This exposes the already-shipped, dependency-free held-out eval metric
(``phantom_training.eval.evaluate``) as a single MCP tool. It invents no new
behaviour — it is a transport shim so mesh agents can call the same computed
proxy metric they get from the ``phantom-train eval`` CLI subcommand.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from phantom_training.eval import evaluate

mcp = FastMCP("phantom-training")


@mcp.tool()
def training_eval(dataset_path: str, holdout_fraction: float = 0.2) -> dict:
    """Compute the deterministic held-out eval floor for an instruction JSONL.

    Wraps the existing ``phantom_training.eval.evaluate``: it splits the alpaca
    rows into train/held-out, runs a nearest-instruction retrieval baseline, and
    returns exact-match + token-F1. This is a lightweight proxy floor (no GPU, no
    model) — a real number computed from the data. Corrupt/too-small datasets are
    reported via a structured ``error`` key rather than raising.
    """
    return evaluate(dataset_path, holdout_fraction=holdout_fraction)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
