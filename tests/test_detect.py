"""Synthetic checks only: no torch, camera, network or model downloads."""

from contextlib import redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import detect


def result(scores=(0.9,), classes=None, names=None):
    def tensor(values):
        return SimpleNamespace(tolist=lambda: values)
    return SimpleNamespace(
        names=names or {0: "person", 1: "bicycle"}, orig_shape=(1440, 2560),
        boxes=SimpleNamespace(
            xyxy=tensor([[1.0, 2.0, 100.0, 200.0] for _ in scores]),
            conf=tensor(list(scores)), cls=tensor(list(classes or [0] * len(scores))),
        ),
    )


class DetectionChecks(unittest.TestCase):
    def test_observation_has_only_supported_claims(self):
        event = detect.observation(result(), camera="test", model="yolo26s.pt", confidence=0.5)
        self.assertEqual(event["event"], "person_detected")
        self.assertEqual(event["schema_version"], 1)
        self.assertEqual(event["person_count"], 1)
        self.assertEqual(event["image_size"], {"width": 2560, "height": 1440})
        self.assertEqual(event["detections"][0]["bbox_xyxy"], [1.0, 2.0, 100.0, 200.0])
        self.assertTrue(event["observed_at"].endswith("+00:00"))
        self.assertNotIn("description", event)
        self.assertNotIn("source", event)
        self.assertNotIn("identity", event)

    def test_threshold_and_class_filter(self):
        event = detect.observation(
            result((0.49, 0.5, 0.99), (0, 0, 1)), camera="test", model="test.pt", confidence=0.5,
        )
        self.assertEqual(event["person_count"], 1)
        self.assertIsNone(detect.observation(result(()), camera="test", model="test.pt", confidence=0.5))
        empty = result()
        empty.boxes = None
        self.assertIsNone(detect.observation(empty, camera="test", model="test.pt", confidence=0.5))

    def test_cooldown_boundary_and_no_people(self):
        sink = io.StringIO()
        times = iter([0.0, 29.999, 30.0])
        counts = detect.write_events(
            [result(), result(()), result(), result()], sink,
            camera="test", model="test.pt", confidence=0.5,
            cooldown_seconds=30, clock=lambda: next(times),
        )
        self.assertEqual(counts, (4, 2))
        self.assertEqual(len([json.loads(line) for line in sink.getvalue().splitlines()]), 2)

    def test_zero_cooldown(self):
        self.assertEqual(detect.write_events(
            [result(), result()], io.StringIO(), camera="test", model="test.pt",
            confidence=0.5, cooldown_seconds=0, clock=lambda: 0,
        ), (2, 2))

    def test_write_error_propagates(self):
        class BrokenOutput(io.StringIO):
            def write(self, value):
                raise OSError("test disk full")
        with self.assertRaises(OSError):
            detect.write_events([result()], BrokenOutput(), camera="test", model="test.pt",
                                confidence=0.5, cooldown_seconds=30)

    def test_bad_model_metadata_rejected(self):
        for sample in (result(names={0: "car"}), result((float("nan"),))):
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                detect.observation(sample, camera="test", model="test.pt", confidence=0.5)

    def test_no_frames_does_not_fabricate_events(self):
        sink = io.StringIO()
        self.assertEqual(detect.write_events([], sink, camera="test", model="test.pt",
                                            confidence=0.5, cooldown_seconds=30), (0, 0))
        self.assertEqual(sink.getvalue(), "")

    def test_argument_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "model.pt"
            model.touch()
            base = ["--source", "rtsp://127.0.0.1:8554/c400", "--model", str(model)]
            self.assertEqual(detect.parse_args(base).confidence, 0.5)
            self.assertEqual(detect.parse_args(base + ["--confidence", "1"]).confidence, 1)
            bad_arguments = [
                ["--confidence", "nan"], ["--confidence", "1.01"],
                ["--confidence", "-0.1"], ["--cooldown-seconds", "-1"],
                ["--cooldown-seconds", "inf"], ["--output", "public.txt"],
                ["--camera", "rtsp://secret"], ["--camera", ""],
                ["--source", "https://example.com/video"],
                ["--source", "rtsp://user:secret@127.0.0.1:8554/c400"],
                ["--source", "rtsp://127.0.0.1:8554/c400?token=secret"],
                ["--source", "rtsp://127.0.0.1:99999/c400"],
                ["--source", "rtsp://[broken/c400"],
                ["--source", "rtsp://192.0.2.1:8554/c400"],
                ["--source", str(Path(directory) / "missing.mp4")],
                ["--model", str(Path(directory) / "missing.pt")],
            ]
            for extra in bad_arguments:
                with self.subTest(extra=extra), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    detect.parse_args(base + extra)
                self.assertEqual(error.exception.code, 2)

    def test_run_with_synthetic_model_and_finite_source(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "events.jsonl"
            args = SimpleNamespace(model=Path(directory) / "test.pt", output=output,
                                   source="test.mp4", device="cpu", camera="test",
                                   confidence=0.5, cooldown_seconds=30)
            flags = {}
            class SyntheticModel:
                names = {0: "person"}
                def predict(self, **kwargs):
                    flags.update(kwargs)
                    yield result()
            with patch.dict("sys.modules", {"ultralytics": SimpleNamespace(YOLO=lambda _: SyntheticModel())}):
                with redirect_stderr(io.StringIO()):
                    detect.run(args)
            self.assertEqual(json.loads(output.read_text())["event"], "person_detected")
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            for name in ["save", "save_txt", "save_crop", "show", "stream_buffer", "nms"]:
                self.assertIs(flags[name], False)
            self.assertEqual(flags["quantize"], 32)

    def test_live_eof_is_failure_with_events_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "events.jsonl"
            args = SimpleNamespace(model=Path(directory) / "test.pt", output=output,
                                   source="rtsp://127.0.0.1:8554/c400", device="cpu",
                                   camera="test", confidence=0.5, cooldown_seconds=30)
            class SyntheticModel:
                names = {0: "person"}
                def predict(self, **kwargs):
                    yield result()
            with patch.dict("sys.modules", {"ultralytics": SimpleNamespace(YOLO=lambda _: SyntheticModel())}):
                with self.assertRaisesRegex(RuntimeError, "live stream ended"):
                    detect.run(args)
            self.assertEqual(json.loads(output.read_text())["person_count"], 1)

    def test_main_failure_and_interrupt(self):
        for failure, code in ((OSError("test disk full"), 1), (KeyboardInterrupt(), 0)):
            with patch("detect.parse_args", return_value=object()), patch("detect.run", side_effect=failure):
                with redirect_stderr(io.StringIO()) as stderr:
                    self.assertEqual(detect.main([]), code)
                self.assertTrue(stderr.getvalue())

    def test_source_integrity(self):
        source_dir = Path(__file__).resolve().parents[1] / "docs" / "sources"
        digest, name = (source_dir / "SHA256SUMS").read_text().strip().split(maxsplit=1)
        self.assertEqual(hashlib.sha256((source_dir / name).read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
