import json
from pathlib import Path

from src.api import models


class PollingFixture:
    def __init__(self, sample_path: Path, batch_size: int = 5) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        self.sample_path = sample_path
        self.batch_size = batch_size
        self._offset = 0

    def poll(self) -> list[models.PollingAPIResponse]:
        responses = get_polling_segment(
            self.sample_path,
            offset=self._offset,
            limit=self.batch_size,
        )
        self._offset += len(responses)
        return responses


def get_polling_segment(
    sample_path: Path,
    offset: int = 0,
    limit: int | None = None,
    *,
    time_since: str | None = None,
) -> list[models.PollingAPIResponse]:
    """Read a fixture segment to simulate responses from the polling source."""
    if time_since is not None:
        try:
            offset = int(time_since)
        except ValueError as exc:
            raise ValueError("time_since must be a nonnegative fixture cursor") from exc
    if offset < 0:
        raise ValueError("time_since must be nonnegative")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")

    responses = []
    response_index = 0
    with sample_path.open(encoding="utf-8") as sample_file:
        for line in sample_file:
            if not line.strip():
                continue
            if response_index < offset:
                response_index += 1
                continue
            if limit is not None and len(responses) == limit:
                break
            responses.append(models.PollingAPIResponse.model_validate(json.loads(line)))
            response_index += 1
    return responses
