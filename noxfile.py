from __future__ import annotations

import nox
from nox.sessions import Session

PACKAGE = "custom_components/lumen"


@nox.session(reuse_venv=True)
def format(session: Session) -> None:
    """Run automatic code formatters"""
    session.run("uv", "sync", external=True)
    session.run("uv", "run", "ruff", "format", ".", external=True)
    session.run("uv", "run", "ruff", "check", "--fix", ".", external=True)


@nox.session(reuse_venv=True)
def tests(session: Session) -> None:
    """Run the complete test suite"""
    session.notify("test_types")
    session.notify("test_style")
    session.notify("test_suite")


@nox.session(reuse_venv=True)
def test_suite(session: Session) -> None:
    """Run the Python-based test suite"""
    session.run("uv", "sync", external=True)
    session.run(
        "uv",
        "run",
        "pytest",
        "tests",
        "--cov=custom_components/lumen",
        "--cov-report",
        "xml",
        "--cov-report",
        "term-missing",
        "-vv",
        external=True,
    )


@nox.session(reuse_venv=True)
def test_types(session: Session) -> None:
    """Check that typing is working as expected"""
    session.run("uv", "sync", external=True)
    session.run("uv", "run", "mypy", "--show-error-codes", PACKAGE, external=True)


@nox.session(reuse_venv=True)
def test_style(session: Session) -> None:
    """Check that style guidelines are being followed"""
    session.run("uv", "sync", external=True)
    session.run("uv", "run", "ruff", "check", PACKAGE, external=True)
    session.run("uv", "run", "ruff", "format", "--check", PACKAGE, external=True)
    session.run("uv", "run", "interrogate", PACKAGE, external=True)
