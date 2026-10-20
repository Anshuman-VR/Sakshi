"""Prometheus text metrics with real observations only."""
from threading import Lock
from sqlalchemy import select, func
from node.models import Decision
from node.services.ledger import LedgerService

_BUCKETS = (0.005, 0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_LOCK = Lock()
_DURATION_COUNT = 0
_DURATION_SUM = 0.0
_DURATION_BUCKETS = {bound: 0 for bound in _BUCKETS}


def observe_verification_duration(seconds: float) -> None:
    global _DURATION_COUNT, _DURATION_SUM
    if seconds < 0:
        return
    with _LOCK:
        _DURATION_COUNT += 1
        _DURATION_SUM += seconds
        for bound in _BUCKETS:
            if seconds <= bound:
                _DURATION_BUCKETS[bound] += 1


def render_metrics(session) -> str:
    counts = dict(session.execute(select(Decision.status, func.count()).group_by(Decision.status)).all())
    lines = [
        "# HELP sakshi_decisions_total Number of decisions by current state",
        "# TYPE sakshi_decisions_total gauge",
    ]
    for status in ("VERIFIED", "FAILED", "EXPIRED", "NOTICE_RECEIVED"):
        lines.append(f'sakshi_decisions_total{{status="{status}"}} {int(counts.get(status, 0))}')
    lines.extend([
        "# HELP sakshi_ledger_seq Highest ledger sequence number",
        "# TYPE sakshi_ledger_seq gauge",
        f"sakshi_ledger_seq {LedgerService.current_sequence(session)}",
        "# HELP sakshi_verification_duration_seconds Verification pipeline duration in seconds",
        "# TYPE sakshi_verification_duration_seconds histogram",
    ])
    with _LOCK:
        for bound in _BUCKETS:
            lines.append(f'sakshi_verification_duration_seconds_bucket{{le="{bound:g}"}} {_DURATION_BUCKETS[bound]}')
        lines.extend([
            f'sakshi_verification_duration_seconds_bucket{{le="+Inf"}} {_DURATION_COUNT}',
            f"sakshi_verification_duration_seconds_count {_DURATION_COUNT}",
            f"sakshi_verification_duration_seconds_sum {_DURATION_SUM:.9f}",
        ])
    lines.extend([
        "# HELP sakshi_sla_breaches_total Number of decisions that breached proof SLA",
        "# TYPE sakshi_sla_breaches_total gauge",
        f"sakshi_sla_breaches_total {int(counts.get('EXPIRED', 0))}",
    ])
    return "\n".join(lines) + "\n"
