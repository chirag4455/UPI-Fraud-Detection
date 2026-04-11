# PHASE 10 REPORT — Advanced Wallet Trust Score (WTS) Enhancements

**Date:** 2026-04-11  
**Status:** ✅ Complete  
**Branch:** copilot/enhance-wallet-trust-score-v2

---

## Overview

Phase 10 enhances the existing Wallet Trust Score (WTS) layer with five advanced
fraud-detection subsystems:

| Subsystem | Detection Target |
|-----------|-----------------|
| Device Geo-Fencing | SIM swap / stolen device / impossible location |
| Velocity Analysis | Impossible travel / rapid-burst transactions |
| Device Fingerprinting | New/compromised devices, long-term trust |
| Payee Network Analysis | First-time payees, high-volume suspicious payees |
| Amount Velocity | Daily overspend, round-number fraud patterns |

All thresholds are **config-driven** via `config.py` (env-var overridable).  
The enhanced layer is **backward compatible**: existing `compute_wts()` call
signatures continue to work without change.

---

## Deliverables

| File | Purpose |
|------|---------|
| `wts_enhancements.py` | All Phase 10 enhancement functions |
| `wts.py` (updated) | Integrates enhancements via optional params |
| `config.py` (updated) | 11 new WTS config parameters |
| `predictor.py` (updated) | Passes Phase 10 optional params to WTS layer |
| `test_wts_enhancements.py` | 45 unit + integration tests |
| `PHASE_10_REPORT.md` | This report |

---

## Module: `wts_enhancements.py`

### Public API

```python
check_geofence(latitude, longitude, user_transactions,
               geofence_radius_km, home_lat, home_lon) -> dict

check_velocity(latitude, longitude, timestamp, user_transactions,
               max_speed_kmh, short_window_minutes, short_window_count) -> dict

check_device_fingerprint(device_id, user_transactions,
                         known_device_threshold, compromise_window_hours,
                         known_device_bonus) -> dict

check_payee_network(payee_upi, user_transactions,
                    all_recent_payee_counts,
                    first_time_penalty, suspicious_sender_threshold) -> dict

check_amount_velocity(amount, user_transactions, timestamp,
                      daily_threshold, round_number_window) -> dict

compute_enhanced_wts_adjustments(...)  # composite; calls all 5 above
```

Each function returns `{"score_delta": float, "flag": bool, "detail": str}`.

### Part 1 — Device Geo-Fencing

- **Haversine formula** (same as base WTS) used for precise great-circle distances.
- **Geofence radius:** 200 km by default (`WTS_GEOFENCE_RADIUS_KM`).
- **Home whitelist:** if `home_lat`/`home_lon` provided and distance ≤ radius → +5 trust, no flag.
- **No history:** first transaction → no penalty.
- **Outside fence:** penalty scales with overshoot distance, capped at −20.

### Part 2 — Velocity Analysis

- **Impossible travel:** compares current and previous transaction location + timestamps.
  Speed > 900 km/h (commercial flight speed) is flagged.
- **Velocity risk score:** `ratio = speed / max_speed` → penalty capped at −25.
- **Rapid burst:** ≥ 5 transactions within 5 minutes → penalty up to −15.
- **Fallback:** if timestamps unavailable, count-based proxy is used.

### Part 3 — Device Fingerprinting

- **New device:** never seen before → −10 trust.
- **Missing device ID:** −5 trust.
- **Partial recognition:** scales linearly up to full known-device bonus.
- **Known device (10+ uses):** +15 trust (`WTS_DEVICE_KNOWN_BONUS`).
- **Compromised device:** same `device_id` appearing in ≥ 2 distinct countries
  within 1 hour → −20 trust, flagged.

### Part 4 — Payee Network Analysis

- **First-time payee:** −15 trust (`WTS_FIRST_TIME_PAYEE_PENALTY`).
- **Frequent payee:** +2 per past transaction, capped at +10.
- **Suspicious payee:** ≥ 100 distinct senders in 1 hour → −20 trust, flagged.

### Part 5 — Amount Velocity

- **Daily threshold:** sum of today's transactions > 1,00,000 INR → penalty up
  to −15 (scales with excess).
- **Round-number pattern:** if ≥ 4 of last 5 transactions and current amount
  are multiples of 1,000 → −5 trust (structuring detection).
- **High amount flagging:** informational note for amounts ≥ 20,000 INR.

---

## `config.py` — New Parameters

| Parameter | Default | Env Variable |
|-----------|---------|-------------|
| `WTS_GEOFENCE_RADIUS_KM` | 200.0 km | `MLBFD_WTS_GEOFENCE_RADIUS_KM` |
| `WTS_MAX_SPEED_KMH` | 900.0 km/h | `MLBFD_WTS_MAX_SPEED_KMH` |
| `WTS_VELOCITY_WINDOW_MINUTES` | 5 min | `MLBFD_WTS_VELOCITY_WINDOW_MINUTES` |
| `WTS_VELOCITY_COUNT_THRESHOLD` | 5 txns | `MLBFD_WTS_VELOCITY_COUNT_THRESHOLD` |
| `WTS_DEVICE_KNOWN_THRESHOLD` | 10 uses | `MLBFD_WTS_DEVICE_KNOWN_THRESHOLD` |
| `WTS_DEVICE_KNOWN_BONUS` | 15.0 pts | `MLBFD_WTS_DEVICE_KNOWN_BONUS` |
| `WTS_DEVICE_COMPROMISE_WINDOW_HOURS` | 1.0 h | `MLBFD_WTS_DEVICE_COMPROMISE_WINDOW_HOURS` |
| `WTS_FIRST_TIME_PAYEE_PENALTY` | 15.0 pts | `MLBFD_WTS_FIRST_TIME_PAYEE_PENALTY` |
| `WTS_SUSPICIOUS_SENDER_THRESHOLD` | 100 senders | `MLBFD_WTS_SUSPICIOUS_SENDER_THRESHOLD` |
| `WTS_DAILY_SPEND_THRESHOLD` | 100,000 INR | `MLBFD_WTS_DAILY_SPEND_THRESHOLD` |

---

## `wts.py` — Integration Changes

`compute_wts()` now accepts three optional Phase 10 parameters:

```python
compute_wts(
    ...,                        # existing params (unchanged)
    timestamp=None,             # for velocity / daily-spend checks
    home_lat=None,              # for geo-fence whitelist
    home_lon=None,              # for geo-fence whitelist
    all_recent_payee_counts=None,  # for suspicious-payee check
)
```

The enhancement result is stored in `components["phase10_enhancement"]` and
`components["phase10_components"]`.  The `explanation` field is augmented with
Phase 10 flags.  A new `enhancement_detail` key is included in the response.

---

## `predictor.py` — Integration Changes

The `predict()` function now passes four additional optional fields from the
transaction dict to `compute_wts()`:

- `txn["timestamp"]`
- `txn["home_lat"]`
- `txn["home_lon"]`
- `txn["all_recent_payee_counts"]`

These fields are optional; if absent the behaviour is identical to Phase 5-9.

---

## Test Results

```
45 tests collected, 45 passed, 0 failed
```

### Test Coverage

| Test Class | Tests | Coverage Area |
|------------|-------|---------------|
| `TestHaversine` | 4 | Distance formula correctness |
| `TestParseTimestamp` | 5 | Timestamp parsing robustness |
| `TestCheckGeofence` | 6 | Geo-fencing scenarios |
| `TestCheckVelocity` | 5 | Velocity / impossible-travel |
| `TestCheckDeviceFingerprint` | 6 | Device recognition / compromise |
| `TestCheckPayeeNetwork` | 5 | Payee trust scenarios |
| `TestCheckAmountVelocity` | 4 | Amount patterns |
| `TestCompositeEnhancedWTS` | 4 | Composite function |
| `TestComputeWTSIntegration` | 6 | End-to-end WTS integration |
| **Total** | **45** | |

---

## Backward Compatibility

- All existing `compute_wts()` call sites work without modification.
- `predictor.py` changes are purely additive (`txn.get(...)` with `None` defaults).
- If `wts_enhancements.py` is missing, `wts.py` degrades gracefully (import
  guard + `logger.warning`).
- API endpoints and response schema are **unchanged**.

---

## Success Criteria

| Criterion | Status |
|-----------|--------|
| Geofencing detection working | ✅ |
| Velocity analysis flagging impossible travel | ✅ |
| Device fingerprinting improving detection | ✅ |
| Payee network analysis operational | ✅ |
| Amount velocity checks operational | ✅ |
| All tests passing (20+) | ✅ 45 tests |
| Backward compatible with Phase 5-9 | ✅ |
| API endpoints unchanged | ✅ |
| Config-driven parameters | ✅ |
