import json
from datetime import date, datetime, time


class TimeInterval:
    def __init__(self, start, end_def):
        if start is None:
            start = date.min
        if end_def is None:
            end_def = date.max
        self.start = start
        self.end = None
        self._setup_start_end(start, end_def)

    def _setup_start_end(self, start, end_def):
        if isinstance(start, datetime):
            self._setup_datetime(start, end_def)
        elif isinstance(start, date):
            self._setup_date(start, end_def)
        elif isinstance(start, time):
            self._setup_time(start, end_def)

    def _setup_datetime(self, start, end_def):
        if isinstance(end_def, datetime):
            self.end = end_def
        elif isinstance(end_def, date):
            self.end = datetime.combine(end_def, time(hour=23, minute=59, second=59))
        elif isinstance(end_def, time):
            self.end = datetime.combine(start.date(), end_def)

    def _setup_date(self, start, end_def):
        if isinstance(end_def, datetime):
            self.end = end_def
            self.start = datetime.combine(start, time(0))
        elif isinstance(end_def, date):
            self.end = end_def
        elif isinstance(end_def, time):
            self.end = datetime.combine(start, end_def)
            self.start = datetime.combine(start, time(0))

    def _setup_time(self, start, end_def):
        if isinstance(end_def, datetime):
            self.start = datetime.combine(end_def.date(), start)
            self.end = end_def
        elif isinstance(end_def, date):
            self.start = datetime.combine(end_def, start)
            self.end = datetime.combine(end_def, time(hour=23, minute=59, second=59))
        elif isinstance(end_def, time):
            # TODO: Change once we support actual time intervals
            pass
            # self.end = end_def
            # self.start = datetime.combine(date.today(), self.start)
            # self.end = datetime.combine(date.today(), end_def)

    def __str__(self):
        return json.dumps({'start': self.start.isoformat(), 'end': self.end.isoformat()})

    def get_start(self):
        return self.start

    def get_end(self):
        return self.end

    def get_first_half(self):
        return TimeInterval(self.start, self.start + (self.end - self.start) / 2)

    def get_second_half(self):
        return TimeInterval(self.start + (self.end - self.start) / 2, self.end)
