"""Compute a task's all-day Calendar period; never writes external data."""
import argparse
import json
from datetime import date, datetime, time, timedelta, timezone


def get_timezone(name):
    if name in ('Asia/Shanghai', 'Asia/Chongqing'):
        return timezone(timedelta(hours=8), name)
    if name in ('UTC', 'Etc/UTC'):
        return timezone.utc
    from zoneinfo import ZoneInfo
    return ZoneInfo(name)


def parse_time(value, tz, end_of_day=False):
    if len(value) == 10:
        day = date.fromisoformat(value)
        return datetime.combine(day, time.max if end_of_day else time.min, tzinfo=tz)
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)


def compute_period(now, deadline, start=None, timezone_name='Asia/Shanghai'):
    tz = get_timezone(timezone_name)
    current = datetime.fromisoformat(now.replace('Z', '+00:00'))
    if current.tzinfo is None:
        raise ValueError('now must include a timezone offset')
    current = current.astimezone(tz)
    cutoff = parse_time(deadline, tz, end_of_day=True)
    reference = parse_time(start, tz) if start else current
    if start and reference > cutoff:
        raise ValueError('task start must not be after its deadline')
    remaining = cutoff - reference
    overdue = cutoff < current
    eligible = remaining > timedelta(days=1) and not overdue
    return {
        'eligible': eligible,
        'overdue': overdue,
        'reference_time': reference.isoformat(),
        'deadline_time': cutoff.isoformat(),
        'remaining_seconds': remaining.total_seconds(),
        'start_date': reference.date().isoformat() if eligible else None,
        'end_date': (cutoff.date() + timedelta(days=1)).isoformat() if eligible else None,
        'transparency': 'transparent',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Current RFC3339 datetime with offset')
    parser.add_argument('--deadline', required=True, help='Deadline date or datetime')
    parser.add_argument('--start', help='Explicit task period start date or datetime')
    parser.add_argument('--timezone', default='Asia/Shanghai')
    args = parser.parse_args()
    try:
        result = compute_period(args.now, args.deadline, args.start, args.timezone)
    except (ValueError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
