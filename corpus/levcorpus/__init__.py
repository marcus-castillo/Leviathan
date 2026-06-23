"""levcorpus — standardized, versioned legal-NLP dataset builder.

Importing this package wires the sibling ``backend/`` directory onto ``sys.path`` (see
``levcorpus.config``) so we can reuse ``app.nlp`` / ``app.embeddings`` / ``app.ingestion`` instead of
duplicating them.
"""
from levcorpus import config  # noqa: F401  (side effect: extends sys.path)

__version__ = "0.1.0"
