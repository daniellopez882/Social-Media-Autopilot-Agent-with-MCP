"""
Refuse to serve on a configuration that cannot work.

Runs at server start (from the FastAPI lifespan) and as a command::

    python -m app.preflight

Exit codes: 0 fit to serve; 78 (EX_CONFIG) otherwise. CI runs it with a
production environment, MOCK_MODE on and no API key, and requires a non-zero
exit -- because the previous code would have started happily on exactly that
configuration and answered every request with mock data.
"""

from __future__ import annotations

import logging
import sys

from app.config import settings

logger = logging.getLogger("socialpilot.preflight")

EXIT_OK = 0
EXIT_CONFIG = 78


def run(*, log: bool = True) -> list[str]:
    problems = settings.problems()
    if log:
        logger.info(
            "environment=%s mock_mode=%s api_key=%s model=%s",
            settings.ENVIRONMENT,
            settings.MOCK_MODE,
            "set" if settings.has_api_key else "UNSET",
            settings.OPENAI_MODEL,
        )
        for problem in problems:
            logger.error("preflight: %s", problem)
        if not problems and settings.MOCK_MODE:
            logger.warning("MOCK_MODE is on: nothing will be published or fetched.")
        if not problems and not settings.has_api_key:
            logger.warning("API_KEY is unset: state-changing routes are open (development only).")
    return problems


def main() -> int:
    logging.basicConfig(level=settings.LOG_LEVEL, format="%(levelname)-8s %(name)s %(message)s")
    problems = run()
    if problems:
        return EXIT_CONFIG
    logger.info("preflight passed")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
