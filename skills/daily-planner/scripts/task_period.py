"""Compute Calendar representations for tasks; never writes external data."""
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


def compute_task_display(now, deadline=None, start=None, planned_date=None,
                         execution_start=None, execution_end=None,
                         timezone_name='Asia/Shanghai'):
    tz = get_timezone(timezone_name)
    current = datetime.fromisoformat(now.replace('Z', '+00:00'))
    if current.tzinfo is None:
        raise ValueError('now must include a timezone offset')
    current = current.astimezone(tz)
    if bool(execution_start) != bool(execution_end):
        raise ValueError('an execution block needs both start and end')
    events = []
    period = compute_period(now, deadline, start, timezone_name) if deadline else None
    if period and period['eligible']:
        events.append({'type': 'period', 'start_date': period['start_date'],
                       'end_date': period['end_date'], 'transparency': 'transparent'})
    if execution_start:
        begin = parse_time(execution_start, tz)
        end = parse_time(execution_end, tz)
        if begin >= end:
            raise ValueError('execution end must be after its start')
        events.append({'type': 'execution', 'start_time': begin.isoformat(),
                       'end_time': end.isoformat(), 'transparency': 'opaque'})
    if not events:
        chosen = planned_date or start or deadline
        display_day = parse_time(chosen, tz).date() if chosen else current.date()
        source = 'planned_date' if planned_date else 'start' if start else 'deadline' if deadline else 'capture_day'
        events.append({'type': 'date_task', 'start_date': display_day.isoformat(),
                       'end_date': (display_day + timedelta(days=1)).isoformat(),
                       'transparency': 'transparent', 'date_source': source})
    return {'events': events, 'period': period,
            'invented_todoist_due_date': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Current RFC3339 datetime with offset')
    parser.add_argument('--deadline', help='Deadline date or datetime')
    parser.add_argument('--start', help='Explicit task period start date or datetime')
    parser.add_argument('--timezone', default='Asia/Shanghai')
    parser.add_argument('--display', action='store_true', help='Choose Calendar entries for any task')
    parser.add_argument('--planned-date')
    parser.add_argument('--execution-start')
    parser.add_argument('--execution-end')
    args = parser.parse_args()
    try:
        if args.display:
            result = compute_task_display(args.now, args.deadline, args.start,
                                          args.planned_date, args.execution_start,
                                          args.execution_end, args.timezone)
        elif args.deadline:
            result = compute_period(args.now, args.deadline, args.start, args.timezone)
        else:
            parser.error('--deadline is required unless --display is used')
    except (ValueError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
