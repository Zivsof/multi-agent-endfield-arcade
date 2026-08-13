"""Turn down library chatter so the agent's own trace is easy to read."""

import logging
import warnings


def silence() -> None:
    warnings.filterwarnings("ignore", message=r".*\[EXPERIMENTAL\].*")
    logging.getLogger("google_genai._api_client").setLevel(logging.ERROR)
    for name in ("google_adk.google.adk.workflow._node_runner", "google_adk.google.adk.runners"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
