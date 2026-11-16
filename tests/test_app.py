import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app


class ShiftTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = app.DB_PATH
        app.DB_PATH = Path(self.tmp.name) / "test.sqlite3"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        app.DB_PATH = self.old_db
        self.tmp.cleanup()

    def request(self, path, method="GET", payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = Request(self.base + path, data=data, method=method,
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    def test_create_list_delete_and_kpis(self):
        payload = {"shift_date": "2026-11-16", "name": "Día", "planned_tonnes": 1200,
                   "actual_tonnes": 1080, "scheduled_minutes": 720, "downtime_minutes": 120}
        status, created = self.request("/api/shifts", "POST", payload)
        self.assertEqual(status, 201)
        self.assertEqual(created["compliance_pct"], 90)
        self.assertAlmostEqual(created["availability_pct"], 83.3)
        self.assertEqual(created["tonnes_per_operating_hour"], 108)
        status, listed = self.request("/api/shifts")
        self.assertEqual(status, 200)
        self.assertEqual(len(listed["shifts"]), 1)
        status, deleted = self.request(f"/api/shifts/{created['id']}", "DELETE")
        self.assertEqual((status, deleted), (200, {"deleted": True}))
        self.assertEqual(self.request("/api/shifts")[1]["shifts"], [])

    def test_reject_invalid_minutes(self):
        payload = {"shift_date": "2026-11-16", "name": "Noche", "planned_tonnes": 100,
                   "actual_tonnes": 90, "scheduled_minutes": 60, "downtime_minutes": 70}
        status, body = self.request("/api/shifts", "POST", payload)
        self.assertEqual(status, 400)
        self.assertIn("minutos", body["error"])

    def test_zero_operating_time_has_no_rate(self):
        payload = {"shift_date": "2026-11-16", "name": "Día", "planned_tonnes": 100,
                   "actual_tonnes": 0, "scheduled_minutes": 60, "downtime_minutes": 60}
        _, created = self.request("/api/shifts", "POST", payload)
        self.assertIsNone(created["tonnes_per_operating_hour"])


if __name__ == "__main__":
    unittest.main()
