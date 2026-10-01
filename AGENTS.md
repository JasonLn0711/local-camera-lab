# Local Camera Lab

This repo owns C400 ingestion research, the person-observation POC and test evidence.
Planning owns priorities, capacity, status and its locator only.

- Keep scope to one camera, go2rtc and YOLO26 until the home acceptance gate passes.
- Preserve supplied source text; write corrections separately with primary URLs and dates.
- Write research notes in Taiwan Traditional Chinese. Separate source reports, implementation,
  synthetic tests, camera tests and measured performance.
- Camera and go2rtc must be on the same subnet for the baseline. Do not assume VPN compatibility.
- No camera login, network scan, installation, GPU run, recording or audio activation without
  authorization for that operation. The current publication does not establish live acceptance.
- Keep credentials, camera addresses, household media/events, models and private logs in ignored
  `.local/`. Only anonymous synthetic examples belong in Git. Never log Xiaomi config or tokens.
- Preserve other repos and running GPU jobs. Do not automatically upgrade host runtime/drivers.
- Reuse Ultralytics ingestion; add PyAV, optimizers or services only for a measured requirement.
- Check with `python3 -m unittest discover -s tests -v`, `python3 detect.py --help`,
  `python3 -m py_compile detect.py` and `git diff --check`. These require no inference packages.
- Update README and the home acceptance record when behavior or verified status changes.
- Publish only explicitly authorized changes; inspect status/staging and never force-push.
