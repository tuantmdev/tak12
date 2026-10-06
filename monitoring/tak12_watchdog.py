#!/usr/bin/env python3
"""Silent TAK12 watchdog: print only when an actionable anomaly is found."""

from __future__ import annotations

from datetime import datetime, timezone

from tak12_monitor import collect

TRACKING_DEPLOYED_AT = datetime(2026, 7, 16, 17, 21, tzinfo=timezone.utc)


def pct_change(current: float, previous: float) -> float | None:
    if previous <= 0:
        return None
    return (current - previous) / previous * 100


def run_checks() -> None:
    data = collect()
    recent = data["gsc"]["recent"]
    previous = data["gsc"]["previous"]
    alerts: list[str] = []

    clicks_change = pct_change(recent["clicks"], previous["clicks"])
    impressions_change = pct_change(recent["impressions"], previous["impressions"])
    if impressions_change is not None and previous["impressions"] >= 500 and impressions_change <= -40:
        alerts.append(
            f"GSC impressions giảm {abs(impressions_change):.1f}% tuần/tuần "
            f"({previous['impressions']} → {recent['impressions']})."
        )

    for status in data["gsc"]["index_status"]:
        if status.get("verdict") != "PASS" or status.get("indexing_state") != "INDEXING_ALLOWED":
            alerts.append(
                f"Index bất thường: {status['url']} — verdict={status.get('verdict')}, "
                f"state={status.get('indexing_state')}, coverage={status.get('coverage')}."
            )

    event_counts = {row[0]: row[1] for row in data["posthog"]["events"]["results"]}
    now = datetime.now(timezone.utc)
    if now - TRACKING_DEPLOYED_AT >= __import__("datetime").timedelta(hours=48):
        if event_counts.get("$pageview", 0) >= 20 and event_counts.get("affiliate_cta_click", 0) == 0:
            alerts.append(
                "PostHog có pageview nhưng chưa ghi nhận affiliate_cta_click sau hơn 48 giờ; "
                "cần kiểm tra event hoặc CTA conversion."
            )

    referral = data["referral"]
    referral_drop = False
    referral_recent = None
    referral_previous = None
    referral_clicks_change = None
    if referral.get("status") == "unavailable":
        alerts.append(
            "Referral unavailable; cần làm mới phiên hoặc kiểm tra collector. "
            "Các kiểm tra GSC/PostHog vẫn được giữ lại."
        )
    else:
        referral_recent = referral["recent"]
        referral_previous = referral["previous"]
        referral_clicks_change = pct_change(
            referral_recent["clickCount"], referral_previous["clickCount"]
        )
        referral_drop = (
            referral_clicks_change is not None
            and referral_previous["clickCount"] >= 20
            and referral_clicks_change <= -40
        )
    gsc_drop = (
        clicks_change is not None
        and previous["clicks"] >= 20
        and clicks_change <= -40
    )
    if gsc_drop or referral_drop:
        details: list[str] = []
        if gsc_drop:
            details.append(
                f"GSC clicks {previous['clicks']} → {recent['clicks']} "
                f"({clicks_change:+.1f}%)"
            )
        if referral_drop:
            details.append(
                f"referral clicks {referral_previous['clickCount']} → "
                f"{referral_recent['clickCount']} ({referral_clicks_change:+.1f}%)"
            )
        alerts.append(
            "Tín hiệu giảm traffic/click tuần-qua-tuần: "
            + "; ".join(details)
            + ". Đây là cảnh báo acquisition cần kiểm tra, không phải kết luận cải tiến/CTA "
              "không hiệu quả. Mẫu 7 ngày còn nhỏ; chỉ so sánh tỷ lệ referral/GSC khi đã xác nhận "
              "hai nguồn có cùng scope và cùng cửa sổ thời gian."
        )
    if alerts:
        print("⚠️ TAK12 — cảnh báo monitoring\n\n" + "\n".join(f"• {item}" for item in alerts))


def main() -> int:
    try:
        run_checks()
    except Exception:
        print(
            "⚠️ TAK12 — lỗi thu thập dữ liệu\n\n"
            "• Collector không hoàn tất; kiểm tra log bảo mật và chạy lại."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
