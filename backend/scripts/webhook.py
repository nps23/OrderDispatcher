import json
from collections.abc import Iterator
from pathlib import Path

from src.api import models


def webhook_bursts(
    sample_path: Path,
    burst_size: int = 25,
) -> Iterator[list[models.WebhookEvent]]:
    if burst_size <= 0:
        raise ValueError("burst_size must be positive")

    burst = []
    with sample_path.open(encoding="utf-8") as sample_file:
        for line in sample_file:
            if not line.strip():
                continue
            burst.append(models.WebhookEvent.model_validate(json.loads(line)))
            if len(burst) == burst_size:
                yield burst
                burst = []
    if burst:
        yield burst
