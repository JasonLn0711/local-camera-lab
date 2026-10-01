# SPDX-License-Identifier: AGPL-3.0-only
"""Single-camera YOLO26 person observations; no image or audio persistence."""

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise argparse.ArgumentTypeError("must be finite")
    return number


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="local video or local go2rtc RTSP URL")
    parser.add_argument("--model", type=Path, default=Path(".local/models/yolo26s.pt"))
    parser.add_argument("--device", default="0", help="0 for the first GPU, or cpu")
    parser.add_argument("--camera", default="c400", help="anonymous source label, not an address")
    parser.add_argument("--confidence", type=finite_float, default=0.5)
    parser.add_argument("--cooldown-seconds", type=finite_float, default=30.0)
    parser.add_argument("--output", type=Path, default=Path(".local/events.jsonl"))
    args = parser.parse_args(argv)
    if not 0 <= args.confidence <= 1:
        parser.error("--confidence must be between 0 and 1")
    if args.cooldown_seconds < 0:
        parser.error("--cooldown-seconds must be nonnegative")
    if not args.camera or len(args.camera) > 64 or not all(
        char.isascii() and (char.isalnum() or char in "_-") for char in args.camera
    ):
        parser.error("--camera must be 1-64 ASCII letters, digits, underscores or hyphens")
    try:
        parsed = urlsplit(args.source)
    except ValueError:
        parser.error("invalid source URL")
    if parsed.scheme:
        if parsed.scheme != "rtsp" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            parser.error("use a loopback rtsp:// go2rtc restream or a local video file")
        if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
            parser.error("keep credentials and camera parameters in private go2rtc config")
        try:
            parsed.port
        except ValueError:
            parser.error("invalid RTSP port")
    elif not Path(args.source).is_file():
        parser.error("local source file does not exist")
    if not args.model.is_file():
        parser.error("model file does not exist; follow README model preparation first")
    if args.output.suffix != ".jsonl":
        parser.error("--output must end in .jsonl (ignored by Git)")
    source_path = Path(args.source).resolve() if not parsed.scheme else None
    if args.output.resolve() in {source_path, args.model.resolve()}:
        parser.error("output must not overwrite the input or model")
    return args


def observation(result, *, camera, model, confidence):
    """Convert one result into observations, without inferring identity or entry."""
    if result.names.get(0) != "person":
        raise ValueError("expected a COCO model whose class 0 is person")
    people = []
    if result.boxes is not None:
        boxes = result.boxes.xyxy.tolist()
        scores = result.boxes.conf.tolist()
        classes = result.boxes.cls.tolist()
        for box, score, label in zip(boxes, scores, classes, strict=True):
            if len(box) != 4 or not all(math.isfinite(value) for value in [*box, score, label]):
                raise ValueError("model returned invalid detection values")
            if label == 0 and score >= confidence:
                people.append({"label": "person", "confidence": score, "bbox_xyxy": box})
    if not people:
        return None
    height, width = result.orig_shape
    return {
        "schema_version": 1,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "camera": camera,
        "event": "person_detected",
        "model": model,
        "person_count": len(people),
        "image_size": {"width": width, "height": height},
        "detections": people,
    }


def write_events(results, sink, *, camera, model, confidence, cooldown_seconds, clock=time.monotonic):
    """At most one observation per cooldown; this is not an occupancy counter."""
    last_emitted = None
    frames = events = 0
    for result in results:
        frames += 1
        event = observation(result, camera=camera, model=model, confidence=confidence)
        if event is None:
            continue
        now = clock()
        if last_emitted is not None and now - last_emitted < cooldown_seconds:
            continue
        sink.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
        sink.flush()
        last_emitted = now
        events += 1
    return frames, events


def run(args):
    # A help request or the stdlib tests must not import torch/download weights.
    from ultralytics import YOLO

    model = YOLO(str(args.model))
    if model.names.get(0) != "person":
        raise ValueError("expected a COCO model whose class 0 is person")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Restrict new output files independently of the caller's umask.
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    results = None
    try:
        with os.fdopen(fd, "a", encoding="utf-8") as sink:
            os.fchmod(sink.fileno(), 0o600)
            results = model.predict(
                source=args.source, stream=True, stream_buffer=False,
                device=args.device, imgsz=640, classes=[0], conf=args.confidence,
                quantize=32, nms=False, save=False, save_txt=False,
                save_crop=False, show=False, verbose=False,
            )
            frames, events = write_events(
                results, sink, camera=args.camera, model=args.model.name,
                confidence=args.confidence, cooldown_seconds=args.cooldown_seconds,
            )
    finally:
        if results is not None:
            results.close()
    if not frames:
        raise RuntimeError("source produced no frames")
    if args.source.startswith("rtsp://"):
        raise RuntimeError("live stream ended; inspect local go2rtc and restart after recovery")
    print(f"Completed: {frames} results, {events} observations", file=sys.stderr)


def main(argv=None):
    args = parse_args(argv)
    try:
        run(args)
    except KeyboardInterrupt:
        print("Stopped; previously flushed observations are retained.", file=sys.stderr)
        return 0
    except Exception as exc:
        # Camera/account configuration is never included in public diagnostics.
        print(f"Detection failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
