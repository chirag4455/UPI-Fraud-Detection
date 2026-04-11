"""
test_wts_enhancements.py — Unit tests for Phase 10 WTS enhancements.

Covers:
  - Haversine distance helper
  - Geo-fencing (within radius, outside radius, home whitelist, no history)
  - Velocity analysis (impossible travel, rapid bursts, normal)
  - Device fingerprinting (new, known, compromised, missing)
  - Payee network analysis (first-time, frequent, suspicious payee)
  - Amount velocity (daily threshold, round-number pattern)
  - Composite compute_enhanced_wts_adjustments
  - Integration: compute_wts with Phase 10 enhancements

Run from the MLBFD_Phase4 directory:
    python -m pytest test_wts_enhancements.py -v
    python test_wts_enhancements.py          (no pytest required)
"""

from __future__ import annotations

import math
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

# Make sure the Phase4 directory is on sys.path
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from wts_enhancements import (
    _haversine_km,
    _parse_timestamp,
    check_geofence,
    check_velocity,
    check_device_fingerprint,
    check_payee_network,
    check_amount_velocity,
    compute_enhanced_wts_adjustments,
)
from wts import compute_wts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _ago(minutes: int) -> str:
    dt = datetime.now(tz=timezone.utc) - timedelta(minutes=minutes)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _make_txn(**overrides) -> dict:
    base = {
        "device_id": "dev_001",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "payee_upi": "merchant@upi",
        "amount": 5000.0,
        "timestamp": _now_iso(),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. _haversine_km
# ---------------------------------------------------------------------------

class TestHaversine(unittest.TestCase):
    def test_same_point_is_zero(self):
        self.assertAlmostEqual(_haversine_km(0, 0, 0, 0), 0.0, places=6)

    def test_known_distance_bangalore_mumbai(self):
        # Bangalore (12.97, 77.59) → Mumbai (19.08, 72.88) ≈ 845 km
        dist = _haversine_km(12.9716, 77.5946, 19.0760, 72.8777)
        self.assertGreater(dist, 800)
        self.assertLess(dist, 900)

    def test_antipodal_points(self):
        dist = _haversine_km(0, 0, 0, 180)
        self.assertAlmostEqual(dist, math.pi * 6371.0, delta=1.0)

    def test_symmetry(self):
        d1 = _haversine_km(10.0, 20.0, 30.0, 40.0)
        d2 = _haversine_km(30.0, 40.0, 10.0, 20.0)
        self.assertAlmostEqual(d1, d2, places=6)


# ---------------------------------------------------------------------------
# 2. _parse_timestamp
# ---------------------------------------------------------------------------

class TestParseTimestamp(unittest.TestCase):
    def test_none_returns_none(self):
        self.assertIsNone(_parse_timestamp(None))

    def test_datetime_passthrough(self):
        dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = _parse_timestamp(dt)
        self.assertEqual(result, dt)

    def test_iso_string(self):
        result = _parse_timestamp("2026-04-11T10:30:00")
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 10)

    def test_unix_float(self):
        result = _parse_timestamp(1700000000.0)
        self.assertIsNotNone(result)

    def test_invalid_string(self):
        self.assertIsNone(_parse_timestamp("not-a-date"))


# ---------------------------------------------------------------------------
# 3. check_geofence
# ---------------------------------------------------------------------------

class TestCheckGeofence(unittest.TestCase):
    def test_no_gps_returns_neutral(self):
        result = check_geofence(None, None, [], geofence_radius_km=200)
        self.assertEqual(result["score_delta"], 0.0)
        self.assertFalse(result["flag"])

    def test_no_history_no_penalty(self):
        result = check_geofence(12.97, 77.59, [], geofence_radius_km=200)
        self.assertEqual(result["score_delta"], 0.0)
        self.assertFalse(result["flag"])

    def test_within_radius_positive_delta(self):
        history = [{"latitude": 12.97, "longitude": 77.59, "timestamp": _ago(60)}]
        result = check_geofence(12.98, 77.60, history, geofence_radius_km=200)
        self.assertGreater(result["score_delta"], 0)
        self.assertFalse(result["flag"])

    def test_outside_radius_negative_delta_and_flag(self):
        # Bangalore → Delhi ~1750 km
        history = [{"latitude": 12.9716, "longitude": 77.5946, "timestamp": _ago(60)}]
        result = check_geofence(28.6139, 77.2090, history, geofence_radius_km=200)
        self.assertLess(result["score_delta"], 0)
        self.assertTrue(result["flag"])

    def test_home_region_whitelist(self):
        history = [{"latitude": 28.6139, "longitude": 77.2090, "timestamp": _ago(60)}]
        result = check_geofence(
            12.9716, 77.5946, history,
            geofence_radius_km=200,
            home_lat=12.9716, home_lon=77.5946,
        )
        self.assertGreater(result["score_delta"], 0)
        self.assertFalse(result["flag"])

    def test_history_without_location_neutral(self):
        history = [{"amount": 100}]
        result = check_geofence(12.97, 77.59, history, geofence_radius_km=200)
        self.assertEqual(result["score_delta"], 0.0)
        self.assertFalse(result["flag"])


# ---------------------------------------------------------------------------
# 4. check_velocity
# ---------------------------------------------------------------------------

class TestCheckVelocity(unittest.TestCase):
    def test_no_location_no_flag(self):
        result = check_velocity(None, None, _now_iso(), [])
        self.assertFalse(result["flag"])
        self.assertEqual(result["score_delta"], 0.0)

    def test_normal_velocity_no_flag(self):
        # 10 km in 30 min = 20 km/h — normal
        history = [
            {
                "latitude": 12.9716,
                "longitude": 77.5946,
                "timestamp": _ago(30),
            }
        ]
        result = check_velocity(12.9800, 77.5950, _now_iso(), history, max_speed_kmh=900)
        self.assertFalse(result["flag"])

    def test_impossible_travel_flagged(self):
        # Delhi → Bangalore in 10 min ≈ 10,500 km/h — impossible
        history = [
            {
                "latitude": 28.6139,
                "longitude": 77.2090,
                "timestamp": _ago(10),
            }
        ]
        result = check_velocity(12.9716, 77.5946, _now_iso(), history, max_speed_kmh=900)
        self.assertTrue(result["flag"])
        self.assertLess(result["score_delta"], 0)

    def test_rapid_burst_flagged(self):
        # 5 transactions within 5 minutes
        history = [
            {"latitude": 12.97, "longitude": 77.59, "timestamp": _ago(i)}
            for i in range(5)
        ]
        result = check_velocity(
            12.97, 77.59, _now_iso(), history,
            short_window_minutes=5, short_window_count=5,
        )
        self.assertTrue(result["flag"])
        self.assertLess(result["score_delta"], 0)

    def test_no_history_no_flag(self):
        result = check_velocity(12.97, 77.59, _now_iso(), [], max_speed_kmh=900)
        self.assertFalse(result["flag"])


# ---------------------------------------------------------------------------
# 5. check_device_fingerprint
# ---------------------------------------------------------------------------

class TestCheckDeviceFingerprint(unittest.TestCase):
    def test_missing_device_id_flagged(self):
        result = check_device_fingerprint(None, [])
        self.assertTrue(result["flag"])
        self.assertLess(result["score_delta"], 0)

    def test_new_device_first_transaction(self):
        result = check_device_fingerprint("dev_new", [])
        self.assertTrue(result["flag"])
        self.assertLess(result["score_delta"], 0)

    def test_new_device_not_in_history(self):
        history = [{"device_id": "dev_old"}]
        result = check_device_fingerprint("dev_new", history)
        self.assertTrue(result["flag"])
        self.assertLess(result["score_delta"], 0)

    def test_known_device_bonus(self):
        history = [{"device_id": "dev_001"} for _ in range(15)]
        result = check_device_fingerprint("dev_001", history, known_device_threshold=10)
        self.assertFalse(result["flag"])
        self.assertGreater(result["score_delta"], 0)

    def test_partial_device_recognition(self):
        history = [{"device_id": "dev_001"} for _ in range(5)]
        result = check_device_fingerprint("dev_001", history, known_device_threshold=10)
        self.assertFalse(result["flag"])
        self.assertGreater(result["score_delta"], 0)

    def test_compromised_device_multi_country(self):
        now = datetime.now(tz=timezone.utc)
        history = [
            {"device_id": "dev_evil", "country": "IN", "timestamp": _ago(20)},
            {"device_id": "dev_evil", "country": "US", "timestamp": _ago(10)},
        ]
        result = check_device_fingerprint("dev_evil", history, compromise_window_hours=1.0)
        self.assertTrue(result["flag"])
        self.assertLess(result["score_delta"], 0)


# ---------------------------------------------------------------------------
# 6. check_payee_network
# ---------------------------------------------------------------------------

class TestCheckPayeeNetwork(unittest.TestCase):
    def test_no_payee_neutral(self):
        result = check_payee_network(None, [])
        self.assertEqual(result["score_delta"], 0.0)
        self.assertFalse(result["flag"])

    def test_first_time_payee_penalty(self):
        result = check_payee_network("new_payee@upi", [], first_time_penalty=15.0)
        self.assertEqual(result["score_delta"], -15.0)
        self.assertTrue(result["flag"])

    def test_frequent_payee_bonus(self):
        history = [{"payee_upi": "merchant@upi"} for _ in range(5)]
        result = check_payee_network("merchant@upi", history)
        self.assertGreater(result["score_delta"], 0)
        self.assertFalse(result["flag"])

    def test_suspicious_payee_flagged(self):
        payee_counts = {"fraud_payee@upi": 150}
        result = check_payee_network(
            "fraud_payee@upi", [],
            all_recent_payee_counts=payee_counts,
            suspicious_sender_threshold=100,
        )
        self.assertTrue(result["flag"])
        self.assertLess(result["score_delta"], 0)

    def test_payee_below_suspicious_threshold(self):
        payee_counts = {"merchant@upi": 50}
        result = check_payee_network(
            "merchant@upi", [],
            all_recent_payee_counts=payee_counts,
            suspicious_sender_threshold=100,
        )
        # Below threshold and new payee → penalty, but not the suspicious one
        self.assertTrue(result["flag"])


# ---------------------------------------------------------------------------
# 7. check_amount_velocity
# ---------------------------------------------------------------------------

class TestCheckAmountVelocity(unittest.TestCase):
    def test_normal_amount_no_flag(self):
        result = check_amount_velocity(1000.0, [], daily_threshold=100000.0)
        self.assertFalse(result["flag"])
        self.assertEqual(result["score_delta"], 0.0)

    def test_daily_threshold_exceeded(self):
        history = [
            {"amount": 40000.0, "timestamp": _now_iso()},
            {"amount": 40000.0, "timestamp": _now_iso()},
        ]
        result = check_amount_velocity(
            30000.0, history, timestamp=_now_iso(), daily_threshold=100000.0
        )
        self.assertTrue(result["flag"])
        self.assertLess(result["score_delta"], 0)

    def test_round_number_pattern_flagged(self):
        history = [{"amount": float(v)} for v in [1000, 2000, 3000, 5000, 10000]]
        result = check_amount_velocity(
            5000.0, history, timestamp=_now_iso(),
            round_number_window=5,
        )
        self.assertTrue(result["flag"])

    def test_no_round_number_no_extra_flag(self):
        history = [{"amount": float(v)} for v in [1234, 5678, 91011, 222, 333]]
        result = check_amount_velocity(
            999.0, history, timestamp=_now_iso(),
            round_number_window=5,
        )
        # Non-round amounts → no round-number flag
        self.assertFalse(result["flag"])


# ---------------------------------------------------------------------------
# 8. compute_enhanced_wts_adjustments (composite)
# ---------------------------------------------------------------------------

class TestCompositeEnhancedWTS(unittest.TestCase):
    def test_returns_expected_keys(self):
        result = compute_enhanced_wts_adjustments(
            device_id="dev_001",
            latitude=12.97,
            longitude=77.59,
            payee_upi="merchant@upi",
            amount=5000.0,
            timestamp=_now_iso(),
            user_transactions=[],
        )
        self.assertIn("total_delta", result)
        self.assertIn("flags", result)
        self.assertIn("components", result)
        self.assertIn("explanation", result)

    def test_all_checks_present(self):
        result = compute_enhanced_wts_adjustments(
            device_id="dev_001",
            latitude=12.97,
            longitude=77.59,
            payee_upi="merchant@upi",
            amount=5000.0,
        )
        expected_checks = {"geofence", "velocity", "device_fingerprint", "payee_network", "amount_velocity"}
        self.assertEqual(set(result["components"].keys()), expected_checks)

    def test_total_delta_sum_of_components(self):
        result = compute_enhanced_wts_adjustments(
            device_id="dev_001",
            latitude=12.97,
            longitude=77.59,
            payee_upi="merchant@upi",
            amount=5000.0,
        )
        expected = sum(c["score_delta"] for c in result["components"].values())
        self.assertAlmostEqual(result["total_delta"], round(expected, 2), places=1)

    def test_no_flags_clean_transaction(self):
        # Known device with history, normal amount, known payee, normal location
        history = [
            {
                "device_id": "dev_trusted",
                "latitude": 12.97,
                "longitude": 77.59,
                "payee_upi": "merchant@upi",
                "amount": 500.0,
                "timestamp": _ago(60 * 24),  # yesterday
            }
        ] * 12  # 12 past transactions → known device
        result = compute_enhanced_wts_adjustments(
            device_id="dev_trusted",
            latitude=12.97,
            longitude=77.59,
            payee_upi="merchant@upi",
            amount=500.0,
            timestamp=_now_iso(),
            user_transactions=history,
            device_known_threshold=10,
        )
        # Should have no geofence or velocity flags
        self.assertNotIn("geofence", result["flags"])
        self.assertNotIn("velocity", result["flags"])


# ---------------------------------------------------------------------------
# 9. Integration: compute_wts with Phase 10 enhancements
# ---------------------------------------------------------------------------

class TestComputeWTSIntegration(unittest.TestCase):
    def test_backward_compatible_basic(self):
        """compute_wts still works with Phase 5-9 call signature."""
        result = compute_wts(
            user_id="user_001",
            device_id="dev_001",
            is_known_device=True,
            latitude=12.97,
            longitude=77.59,
            payee_upi="merchant@upi",
            amount=5000.0,
            user_transactions=[],
        )
        self.assertIn("score", result)
        self.assertIn("components", result)
        self.assertIn("explanation", result)
        self.assertGreaterEqual(result["score"], 0.0)
        self.assertLessEqual(result["score"], 100.0)

    def test_with_phase10_params(self):
        """compute_wts accepts Phase 10 optional params without error."""
        result = compute_wts(
            user_id="user_002",
            device_id="dev_002",
            is_known_device=True,
            latitude=12.97,
            longitude=77.59,
            payee_upi="merchant@upi",
            amount=5000.0,
            user_transactions=[],
            timestamp=_now_iso(),
            home_lat=12.97,
            home_lon=77.59,
        )
        self.assertIn("score", result)
        self.assertGreaterEqual(result["score"], 0.0)
        self.assertLessEqual(result["score"], 100.0)

    def test_impossible_travel_reduces_score(self):
        """Impossible-travel scenario should lower WTS vs normal scenario."""
        history_normal = [
            {
                "device_id": "dev_ok",
                "latitude": 12.9716,
                "longitude": 77.5946,
                "payee_upi": "merchant@upi",
                "timestamp": _ago(30),
            }
        ]
        # Normal: same city
        normal = compute_wts(
            user_id="u1", device_id="dev_ok", is_known_device=True,
            latitude=12.9720, longitude=77.5950,
            payee_upi="merchant@upi", amount=5000.0,
            user_transactions=history_normal, timestamp=_now_iso(),
        )
        # Fraud: Delhi → Bangalore in 10 min
        fraud_history = [
            {
                "device_id": "dev_ok",
                "latitude": 28.6139,
                "longitude": 77.2090,
                "payee_upi": "merchant@upi",
                "timestamp": _ago(10),
            }
        ]
        fraud = compute_wts(
            user_id="u1", device_id="dev_ok", is_known_device=True,
            latitude=12.9716, longitude=77.5946,
            payee_upi="merchant@upi", amount=5000.0,
            user_transactions=fraud_history, timestamp=_now_iso(),
        )
        self.assertLess(fraud["score"], normal["score"])

    def test_known_device_bonus_applied(self):
        """Known device seen 10+ times earns the Phase 10 device bonus."""
        history = [{"device_id": "dev_trusted", "timestamp": _ago(i * 60)} for i in range(15)]
        result = compute_wts(
            user_id="u3", device_id="dev_trusted", is_known_device=True,
            latitude=None, longitude=None,
            payee_upi=None, amount=1000.0,
            user_transactions=history, timestamp=_now_iso(),
        )
        self.assertIn("phase10_enhancement", result["components"])
        self.assertGreater(result["components"]["phase10_enhancement"], 0)

    def test_score_clamped_between_0_and_100(self):
        result = compute_wts(
            user_id="u4", device_id=None, is_known_device=False,
            latitude=28.61, longitude=77.20,
            payee_upi="scammer@upi", amount=500000.0,
            user_transactions=None, timestamp=_now_iso(),
        )
        self.assertGreaterEqual(result["score"], 0.0)
        self.assertLessEqual(result["score"], 100.0)

    def test_enhancement_detail_in_output(self):
        result = compute_wts(
            user_id="u5", device_id="dev_005", is_known_device=False,
            latitude=12.97, longitude=77.59,
            payee_upi="merchant@upi", amount=5000.0,
            user_transactions=[],
        )
        self.assertIn("enhancement_detail", result)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
