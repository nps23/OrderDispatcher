import argparse # TODO: Move to click
import json
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scripts import webhook as webhook_mock
from src.api.models import WebhookEvent


DEFAULT_SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data"
API_URL = "http://localhost:9000"


def _request(
    url: str,
    *,
    data: bytes,
    content_type: str,
) -> bytes:
    request = Request(
        url,
        data=data,
        headers={"Content-Type": content_type},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return response.read()
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Request to {url} failed: {exc}") from exc


def _webhook_request(payload: WebhookEvent, run_id: str, cycle: int) -> bytes:
    event_id = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"{payload.order_id}:{run_id}:{cycle}",
    )
    event = payload.model_copy(update={"order_id": event_id})
    return event.model_dump_json().encode("utf-8")


def _upload_csv(csv_path: Path) -> dict[str, object]:
    boundary = f"order-dispatcher-{uuid.uuid4().hex}"
    filename = csv_path.name.replace('"', "")
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: text/csv\r\n\r\n"
    ).encode("utf-8")
    body += csv_path.read_bytes()
    body += f"\r\n--{boundary}--\r\n".encode("ascii")
    response = _request(
        f"{API_URL}/ingest/csv",
        data=body,
        content_type=f"multipart/form-data; boundary={boundary}",
    )
    return json.loads(response)


def upload_csv(csv_path: Path) -> dict[str, object]:
    return _upload_csv(csv_path)


def _simulate_bursts_impl(
    sample_path: Path,
    *,
    burst_size: int,
    sleep_seconds: float,
) -> None:
    if burst_size <= 0:
        raise ValueError("burst_size must be positive")
    if sleep_seconds < 0:
        raise ValueError("sleep_seconds must be nonnegative")

    run_id = uuid.uuid4().hex
    cycle = 0
    while True:
        found_orders = False
        for burst in webhook_mock.webhook_bursts(sample_path, burst_size):
            found_orders = True
            for payload in burst:
                _request(
                    f"{API_URL}/ingest/webhook",
                    data=_webhook_request(payload, run_id, cycle),
                    content_type="application/json",
                )
            print(f"Sent burst of {len(burst)} orders (cycle {cycle})", flush=True)
            time.sleep(sleep_seconds)
        if not found_orders:
            raise ValueError(f"No webhook orders found in {sample_path}")
        cycle += 1


def simulate_bursts(
    sample_path: Path,
    *,
    burst_size: int,
    sleep_seconds: float,
) -> None:
    _simulate_bursts_impl(
        sample_path,
        burst_size=burst_size,
        sleep_seconds=sleep_seconds,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Test order pipeline endpoints with sample CSV or webhook data."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    csv_parser = subparsers.add_parser(
        "upload-csv", help="Upload a CSV file through POST /ingest/csv"
    )
    csv_parser.add_argument("path", type=Path)

    burst_parser = subparsers.add_parser(
        "simulate-bursts", help="Continuously POST webhook sample orders in bursts"
    )
    burst_parser.add_argument(
        "--sample",
        type=Path,
        default=DEFAULT_SAMPLE_DIR / "webhook_orders.jsonl",
    )
    burst_parser.add_argument("--burst-size", type=int, default=25)
    burst_parser.add_argument("--sleep-seconds", type=float, default=2)

    args = parser.parse_args(argv)
    try:
        if args.command == "upload-csv":
            print(json.dumps(_upload_csv(args.path), indent=2))
        else:
            _simulate_bursts_impl(
                args.sample,
                burst_size=args.burst_size,
                sleep_seconds=args.sleep_seconds,
            )
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    except KeyboardInterrupt:
        print("Stopped.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
