"""Tests for gtimelog.timelog"""

import datetime
import doctest
import os
import re
import shutil
import tempfile
import textwrap
import unittest
import sys
from pprint import pprint
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

import freezegun
import mock

from gtimelog.timelog import TimeLog


class Checker(doctest.OutputChecker):
    """Doctest output checker that can deal with unicode literals."""

    def check_output(self, want, got, optionflags):
        # u'...' -> '...'; u"..." -> "..."
        got = re.sub(r'''\bu('[^']*'|"[^"]*")''', r'\1', got)
        return doctest.OutputChecker.check_output(self, want, got, optionflags)


def doctest_as_hours():
    """Tests for as_hours

        >>> from gtimelog.timelog import as_hours
        >>> from datetime import timedelta
        >>> as_hours(timedelta(0))
        0.0
        >>> as_hours(timedelta(minutes=30))
        0.5
        >>> as_hours(timedelta(minutes=60))
        1.0
        >>> as_hours(timedelta(days=2))
        48.0

    """


def doctest_format_duration():
    """Tests for format_duration.

        >>> from gtimelog.timelog import format_duration
        >>> from datetime import timedelta
        >>> format_duration(timedelta(0))
        '0 h 0 min'
        >>> format_duration(timedelta(minutes=1))
        '0 h 1 min'
        >>> format_duration(timedelta(minutes=60))
        '1 h 0 min'

    """


def doctest_format_short():
    """Tests for format_duration_short.

        >>> from gtimelog.timelog import format_duration_short
        >>> from datetime import timedelta
        >>> format_duration_short(timedelta(0))
        '0:00'
        >>> format_duration_short(timedelta(minutes=1))
        '0:01'
        >>> format_duration_short(timedelta(minutes=59))
        '0:59'
        >>> format_duration_short(timedelta(minutes=60))
        '1:00'
        >>> format_duration_short(timedelta(days=1, hours=2, minutes=3))
        '26:03'

    """


def doctest_format_duration_long():
    """Tests for format_duration_long.

        >>> from gtimelog.timelog import format_duration_long
        >>> from datetime import timedelta
        >>> format_duration_long(timedelta(0))
        '0 min'
        >>> format_duration_long(timedelta(minutes=1))
        '1 min'
        >>> format_duration_long(timedelta(minutes=60))
        '1 hour'
        >>> format_duration_long(timedelta(minutes=65))
        '1 hour 5 min'
        >>> format_duration_long(timedelta(hours=2))
        '2 hours'
        >>> format_duration_long(timedelta(hours=2, minutes=1))
        '2 hours 1 min'

    """


def doctest_parse_datetime():
    """Tests for parse_datetime

        >>> from gtimelog.timelog import parse_datetime
        >>> parse_datetime('2005-02-03 02:13')
        datetime.datetime(2005, 2, 3, 2, 13)
        >>> parse_datetime('xyzzy')
        Traceback (most recent call last):
          ...
        ValueError: bad date time: 'xyzzy'
        >>> parse_datetime('YYYY-MM-DD HH:MM')
        Traceback (most recent call last):
          ...
        ValueError: bad date time: 'YYYY-MM-DD HH:MM'

    """


def doctest_parse_time():
    """Tests for parse_time

        >>> from gtimelog.timelog import parse_time
        >>> parse_time('02:13')
        datetime.time(2, 13)
        >>> parse_time('xyzzy')
        Traceback (most recent call last):
          ...
        ValueError: bad time: 'xyzzy'

    """


def doctest_virtual_day():
    """Tests for virtual_day

        >>> from datetime import datetime, time
        >>> from gtimelog.timelog import virtual_day

    Virtual midnight

        >>> vm = time(2, 0)

    The tests themselves:

        >>> virtual_day(datetime(2005, 2, 3, 1, 15), vm)
        datetime.date(2005, 2, 2)
        >>> virtual_day(datetime(2005, 2, 3, 1, 59), vm)
        datetime.date(2005, 2, 2)
        >>> virtual_day(datetime(2005, 2, 3, 2, 0), vm)
        datetime.date(2005, 2, 3)
        >>> virtual_day(datetime(2005, 2, 3, 12, 0), vm)
        datetime.date(2005, 2, 3)
        >>> virtual_day(datetime(2005, 2, 3, 23, 59), vm)
        datetime.date(2005, 2, 3)

    """


def doctest_different_days():
    """Tests for different_days

        >>> from datetime import datetime, time
        >>> from gtimelog.timelog import different_days

    Virtual midnight

        >>> vm = time(2, 0)

    The tests themselves:

        >>> different_days(datetime(2005, 2, 3, 1, 15),
        ...                datetime(2005, 2, 3, 2, 15), vm)
        True
        >>> different_days(datetime(2005, 2, 3, 11, 15),
        ...                datetime(2005, 2, 3, 12, 15), vm)
        False

    """


def doctest_first_of_month():
    """Tests for first_of_month

        >>> from gtimelog.timelog import first_of_month
        >>> from datetime import date, timedelta

        >>> first_of_month(date(2007, 1, 1))
        datetime.date(2007, 1, 1)

        >>> first_of_month(date(2007, 1, 7))
        datetime.date(2007, 1, 1)

        >>> first_of_month(date(2007, 1, 31))
        datetime.date(2007, 1, 1)

        >>> first_of_month(date(2007, 2, 1))
        datetime.date(2007, 2, 1)

        >>> first_of_month(date(2007, 2, 28))
        datetime.date(2007, 2, 1)

        >>> first_of_month(date(2007, 3, 1))
        datetime.date(2007, 3, 1)

    Why not test extensively?

        >>> d = date(2000, 1, 1)
        >>> while d < date(2005, 1, 1):
        ...     f = first_of_month(d)
        ...     if (f.year, f.month, f.day) != (d.year, d.month, 1):
        ...         print("WRONG: first_of_month(%r) returned %r" % (d, f))
        ...     d += timedelta(1)

    """


def doctest_next_month():
    """Tests for next_month

        >>> from gtimelog.timelog import next_month
        >>> from datetime import date, timedelta

        >>> next_month(date(2007, 1, 1))
        datetime.date(2007, 2, 1)

        >>> next_month(date(2007, 1, 7))
        datetime.date(2007, 2, 1)

        >>> next_month(date(2007, 1, 31))
        datetime.date(2007, 2, 1)

        >>> next_month(date(2007, 2, 1))
        datetime.date(2007, 3, 1)

        >>> next_month(date(2007, 2, 28))
        datetime.date(2007, 3, 1)

        >>> next_month(date(2007, 3, 1))
        datetime.date(2007, 4, 1)

    Why not test extensively?

        >>> d = date(2000, 1, 1)
        >>> while d < date(2005, 1, 1):
        ...     f = next_month(d)
        ...     prev = f - timedelta(1)
        ...     if f.day != 1 or (prev.year, prev.month) != (d.year, d.month):
        ...         print("WRONG: next_month(%r) returned %r" % (d, f))
        ...     d += timedelta(1)

    """


def doctest_uniq():
    """Tests for uniq

        >>> from gtimelog.timelog import uniq
        >>> uniq(['a', 'b', 'b', 'c', 'd', 'b', 'd'])
        ['a', 'b', 'c', 'd', 'b', 'd']
        >>> uniq(['a'])
        ['a']
        >>> uniq([])
        []

    """


def make_time_window(file=None, min=None, max=None, vm=datetime.time(2)):
    from gtimelog.timelog import TimeLog
    if file is None:
        file = StringIO()
    return TimeLog(file, vm).window_for(min, max)


def doctest_TimeWindow_repr():
    """Test for TimeWindow.__repr__

        >>> from datetime import datetime, time
        >>> min = datetime(2013, 12, 3)
        >>> max = datetime(2013, 12, 4)
        >>> vm = time(2, 0)

        >>> make_time_window(min=min, max=max, vm=vm)
        <TimeWindow: 2013-12-03 00:00:00..2013-12-04 00:00:00>

    """


def doctest_TimeWindow_reread_no_file():
    """Test for TimeWindow.reread

        >>> window = make_time_window('/nosuchfile')

    There's no error.

        >>> len(window.items)
        0
        >>> window.last_time()

    """


def doctest_TimeWindow_reread_bad_timestamp():
    """Test for TimeWindow.reread

        >>> from datetime import datetime, time
        >>> min = datetime(2013, 12, 4)
        >>> max = datetime(2013, 12, 5)
        >>> vm = time(2, 0)

        >>> sampledata = StringIO('''
        ... 2013-12-04 09:00: start **
        ... # hey: this is not a timestamp
        ... 2013-12-04 09:14: gtimelog: write some tests
        ... ''')

        >>> window = make_time_window(sampledata, min, max, vm)

    There's no error, the line with a bad timestamp is silently skipped.

        >>> len(window.items)
        2

    """


def doctest_TimeWindow_reread_bad_ordering():
    """Test for TimeWindow.reread

        >>> from datetime import datetime
        >>> min = datetime(2013, 12, 4)
        >>> max = datetime(2013, 12, 5)

        >>> sampledata = StringIO('''
        ... 2013-12-04 09:00: start **
        ... 2013-12-04 09:14: gtimelog: write some tests
        ... 2013-12-04 09:10: gtimelog: whoops clock got all confused
        ... 2013-12-04 09:10: gtimelog: so this will need to be fixed
        ... ''')

        >>> window = make_time_window(sampledata, min, max)

    There's no error, the timestamps have been reordered, but note that
    order was preserved for events with the same timestamp

        >>> for t, e in window.items:
        ...     print("%s: %s" % (t.strftime('%H:%M'), e))
        09:00: start **
        09:10: gtimelog: whoops clock got all confused
        09:10: gtimelog: so this will need to be fixed
        09:14: gtimelog: write some tests

        >>> window.last_time()
        datetime.datetime(2013, 12, 4, 9, 14)

    """


def doctest_TimeWindow_count_days():
    """Test for TimeWindow.count_days

        >>> from datetime import datetime, time
        >>> min = datetime(2013, 12, 2)
        >>> max = datetime(2013, 12, 9)
        >>> vm = time(2, 0)

        >>> sampledata = StringIO('''
        ... 2013-12-04 09:00: start **
        ... 2013-12-04 09:14: gtimelog: write some tests
        ... 2013-12-04 09:10: gtimelog: whoops clock got all confused
        ... 2013-12-04 09:10: gtimelog: so this will need to be fixed
        ...
        ... 2013-12-05 22:30: some fictional late night work **
        ... 2013-12-06 00:30: frobnicate the widgets
        ...
        ... 2013-12-08 09:00: work **
        ... 2013-12-08 09:01: and stuff
        ... ''')

        >>> window = make_time_window(sampledata, min, max, vm)
        >>> window.count_days()
        3

    """


def doctest_TimeWindow_last_entry():
    """Test for TimeWindow.last_entry

        >>> from datetime import datetime
        >>> window = make_time_window()

    Case #1: no items

        >>> window.items = []
        >>> window.last_entry()

    Case #2: single item

        >>> window.items = [
        ...     (datetime(2013, 12, 4, 9, 0), 'started **'),
        ... ]
        >>> start, stop, duration, tags, entry = window.last_entry()
        >>> start == stop == datetime(2013, 12, 4, 9, 0)
        True
        >>> duration
        datetime.timedelta(0)
        >>> entry
        'started **'

    Case #3: single item at start of new day

        >>> window.items = [
        ...     (datetime(2013, 12, 3, 12, 0), 'stuff'),
        ...     (datetime(2013, 12, 4, 9, 0), 'started **'),
        ... ]
        >>> start, stop, duration, tags, entry = window.last_entry()
        >>> start == stop == datetime(2013, 12, 4, 9, 0)
        True
        >>> duration
        datetime.timedelta(0)
        >>> entry
        'started **'


    Case #4: several items

        >>> window.items = [
        ...     (datetime(2013, 12, 4, 9, 0), 'started **'),
        ...     (datetime(2013, 12, 4, 9, 31), 'gtimelog: tests'),
        ... ]
        >>> start, stop, duration, tags, entry = window.last_entry()
        >>> start
        datetime.datetime(2013, 12, 4, 9, 0)
        >>> stop
        datetime.datetime(2013, 12, 4, 9, 31)
        >>> duration
        datetime.timedelta(0, 1860)
        >>> entry
        'gtimelog: tests'

    """


def doctest_Exports_to_csv_complete():
    r"""Tests for Exports.to_csv_complete

        >>> from datetime import datetime, time
        >>> min = datetime(2008, 6, 1)
        >>> max = datetime(2008, 7, 1)
        >>> vm = time(2, 0)

        >>> sampledata = StringIO('''
        ... 2008-06-03 12:45: start
        ... 2008-06-03 13:00: something
        ... 2008-06-03 14:45: something else
        ... 2008-06-03 15:45: etc
        ... 2008-06-05 12:45: start
        ... 2008-06-05 13:15: something
        ... 2008-06-05 14:15: rest **
        ... 2008-06-05 16:15: let's not mention this ever again ***
        ... ''')

        >>> window = make_time_window(sampledata, min, max, vm)

        >>> from gtimelog.timelog import Exports
        >>> Exports(window).to_csv_complete(sys.stdout)
        task,time (minutes)
        etc,60
        something,45
        something else,105

    """


def doctest_Exports_to_csv_daily():
    r"""Tests for Exports.to_csv_daily

        >>> from datetime import datetime, time
        >>> min = datetime(2008, 6, 1)
        >>> max = datetime(2008, 7, 1)
        >>> vm = time(2, 0)

        >>> sampledata = StringIO('''
        ... 2008-06-03 12:45: start
        ... 2008-06-03 13:00: something
        ... 2008-06-03 14:45: something else
        ... 2008-06-03 15:45: etc
        ... 2008-06-05 12:45: start
        ... 2008-06-05 13:15: something
        ... 2008-06-05 14:15: rest **
        ... ''')

        >>> window = make_time_window(sampledata, min, max, vm)

        >>> from gtimelog.timelog import Exports
        >>> Exports(window).to_csv_daily(sys.stdout)
        date,day-start (hours),slacking (hours),work (hours)
        2008-06-03,12.75,0.0,3.0
        2008-06-04,0.0,0.0,0.0
        2008-06-05,12.75,1.0,0.5

    """


def doctest_Exports_icalendar():
    r"""Tests for Exports.icalendar

        >>> from datetime import datetime, time
        >>> min = datetime(2008, 6, 1)
        >>> max = datetime(2008, 7, 1)
        >>> vm = time(2, 0)

        >>> sampledata = StringIO(r'''
        ... 2008-06-03 12:45: start **
        ... 2008-06-03 13:00: something
        ... 2008-06-03 15:45: something, else; with special\chars
        ... 2008-06-05 12:45: start **
        ... 2008-06-05 13:15: something
        ... 2008-06-05 14:15: rest **
        ... ''')

        >>> window = make_time_window(sampledata, min, max, vm)

        >>> from gtimelog.timelog import Exports

        >>> with freezegun.freeze_time("2015-05-18 15:40"):
        ...     with mock.patch('socket.getfqdn') as mock_getfqdn:
        ...         mock_getfqdn.return_value = 'localhost'
        ...         Exports(window).icalendar(sys.stdout)
        ... # doctest: +REPORT_NDIFF
        BEGIN:VCALENDAR
        PRODID:-//gtimelog.org/NONSGML GTimeLog//EN
        VERSION:2.0
        BEGIN:VEVENT
        UID:be5f9be205c2308f7f1a30d6c399d6bd@localhost
        SUMMARY:start **
        DTSTART:20080603T124500
        DTEND:20080603T124500
        DTSTAMP:20150518T154000Z
        END:VEVENT
        BEGIN:VEVENT
        UID:33c7e212fed11eda71d5acd4bd22119b@localhost
        SUMMARY:something
        DTSTART:20080603T124500
        DTEND:20080603T130000
        DTSTAMP:20150518T154000Z
        END:VEVENT
        BEGIN:VEVENT
        UID:b10c11beaf91df16964a46b4c87420b1@localhost
        SUMMARY:something\, else\; with special\\chars
        DTSTART:20080603T130000
        DTEND:20080603T154500
        DTSTAMP:20150518T154000Z
        END:VEVENT
        BEGIN:VEVENT
        UID:04964eef67ec22178d74fe4c0f06aa2a@localhost
        SUMMARY:start **
        DTSTART:20080605T124500
        DTEND:20080605T124500
        DTSTAMP:20150518T154000Z
        END:VEVENT
        BEGIN:VEVENT
        UID:2b51ea6d1c26f02d58051a691657068d@localhost
        SUMMARY:something
        DTSTART:20080605T124500
        DTEND:20080605T131500
        DTSTAMP:20150518T154000Z
        END:VEVENT
        BEGIN:VEVENT
        UID:bd6bfd401333dbbf34fec941567d5d06@localhost
        SUMMARY:rest **
        DTSTART:20080605T131500
        DTEND:20080605T141500
        DTSTAMP:20150518T154000Z
        END:VEVENT
        END:VCALENDAR

    """


def doctest_Reports_weekly_report_categorized():
    r"""Tests for Reports.weekly_report_categorized

        >>> from datetime import datetime
        >>> from gtimelog.timelog import Reports

        >>> min = datetime(2010, 1, 25)
        >>> max = datetime(2010, 1, 31)

        >>> window = make_time_window(min=min, max=max)
        >>> reports = Reports(window)
        >>> reports.weekly_report_categorized(sys.stdout, 'foo@bar.com',
        ...                                   'Bob Jones')
        To: foo@bar.com
        Subject: Weekly report for Bob Jones (week 04)
        <BLANKLINE>
        No work done this week.

        >>> fh = StringIO('\n'.join([
        ...    '2010-01-30 09:00: start',
        ...    '2010-01-30 09:23: Bing: stuff',
        ...    '2010-01-30 12:54: Bong: other stuff',
        ...    '2010-01-30 13:32: lunch **',
        ...    '2010-01-30 23:46: misc',
        ...    '']))

        >>> window = make_time_window(fh, min, max)
        >>> reports = Reports(window)
        >>> reports.weekly_report_categorized(sys.stdout, 'foo@bar.com',
        ...                                   'Bob Jones')
        To: foo@bar.com
        Subject: Weekly report for Bob Jones (week 04)
        <BLANKLINE>
                                                                        time
        Bing:
        <BLANKLINE>
          Stuff                                                           0:23
        ----------------------------------------------------------------------
                                                                          0:23
        <BLANKLINE>
        Bong:
        <BLANKLINE>
          Other stuff                                                     3:31
        ----------------------------------------------------------------------
                                                                          3:31
        <BLANKLINE>
        No category:
        <BLANKLINE>
          Misc                                                           10:14
        ----------------------------------------------------------------------
                                                                         10:14
        <BLANKLINE>
        Total work done this week: 14:08
        <BLANKLINE>
        Categories by time spent:
          No category     10:14
          Bong             3:31
          Bing             0:23

    """


def doctest_Reports_monthly_report_categorized():
    r"""Tests for Reports.monthly_report_categorized

        >>> from datetime import datetime, time
        >>> from gtimelog.timelog import Reports

        >>> vm = time(2, 0)
        >>> min = datetime(2010, 1, 25)
        >>> max = datetime(2010, 1, 31)

        >>> window = make_time_window(min=min, max=max)
        >>> reports = Reports(window)
        >>> reports.monthly_report_categorized(sys.stdout, 'foo@bar.com',
        ...                                   'Bob Jones')
        To: foo@bar.com
        Subject: Monthly report for Bob Jones (2010/01)
        <BLANKLINE>
        No work done this month.

        >>> fh = StringIO('\n'.join([
        ...    '2010-01-30 09:00: start',
        ...    '2010-01-30 09:23: Bing: stuff',
        ...    '2010-01-30 12:54: Bong: other stuff',
        ...    '2010-01-30 13:32: lunch **',
        ...    '2010-01-30 23:46: misc',
        ...    '']))

        >>> window = make_time_window(fh, min, max, vm)
        >>> reports = Reports(window)
        >>> reports.monthly_report_categorized(sys.stdout, 'foo@bar.com',
        ...                                   'Bob Jones')
        To: foo@bar.com
        Subject: Monthly report for Bob Jones (2010/01)
        <BLANKLINE>
                                                                          time
        Bing:
          Stuff                                                           0:23
        ----------------------------------------------------------------------
                                                                          0:23
        <BLANKLINE>
        Bong:
          Other stuff                                                     3:31
        ----------------------------------------------------------------------
                                                                          3:31
        <BLANKLINE>
        No category:
          Misc                                                           10:14
        ----------------------------------------------------------------------
                                                                         10:14
        <BLANKLINE>
        Total work done this month: 14:08
        <BLANKLINE>
        Categories by time spent:
          No category     10:14
          Bong             3:31
          Bing             0:23

    """


def doctest_Reports_report_categories():
    r"""Tests for Reports._report_categories

        >>> from datetime import datetime, time, timedelta
        >>> from gtimelog.timelog import Reports

        >>> vm = time(2, 0)
        >>> min = datetime(2010, 1, 25)
        >>> max = datetime(2010, 1, 31)

        >>> categories = {
        ...    'Bing': timedelta(2),
        ...    None: timedelta(1)}

        >>> window = make_time_window(StringIO(), min, max, vm)
        >>> reports = Reports(window)
        >>> reports._report_categories(sys.stdout, categories)
        <BLANKLINE>
        By category:
        <BLANKLINE>
        Bing                                                            48 hours
        (none)                                                          24 hours
        <BLANKLINE>

    """


def doctest_Reports_daily_report():
    r"""Tests for Reports.daily_report

        >>> from datetime import datetime, time
        >>> from gtimelog.timelog import Reports

        >>> vm = time(2, 0)
        >>> min = datetime(2010, 1, 30)
        >>> max = datetime(2010, 1, 31)

        >>> window = make_time_window(StringIO(), min, max, vm)
        >>> reports = Reports(window)
        >>> reports.daily_report(sys.stdout, 'foo@bar.com', 'Bob Jones')
        To: foo@bar.com
        Subject: 2010-01-30 report for Bob Jones (Sat, week 04)
        <BLANKLINE>
        No work done today.

        >>> fh = StringIO('\n'.join([
        ...    '2010-01-30 09:00: start',
        ...    '2010-01-30 09:23: Bing: stuff',
        ...    '2010-01-30 12:54: Bong: other stuff',
        ...    '2010-01-30 13:32: lunch **',
        ...    '2010-01-30 15:46: misc',
        ...    '']))

        >>> window = make_time_window(fh, min, max, vm)
        >>> reports = Reports(window)
        >>> reports.daily_report(sys.stdout, 'foo@bar.com', 'Bob Jones')
        To: foo@bar.com
        Subject: 2010-01-30 report for Bob Jones (Sat, week 04)
        <BLANKLINE>
        Start at 09:00
        <BLANKLINE>
        Bing: stuff                                                     23 min
        Bong: other stuff                                               3 hours 31 min
        Misc                                                            2 hours 14 min
        <BLANKLINE>
        Total work done: 6 hours 8 min
        <BLANKLINE>
        By category:
        <BLANKLINE>
        Bing                                                            23 min
        Bong                                                            3 hours 31 min
        (none)                                                          2 hours 14 min
        <BLANKLINE>
        Slacking:
        <BLANKLINE>
        Lunch **                                                        38 min
        <BLANKLINE>
        Time spent slacking: 38 min

    """


def doctest_Reports_weekly_report_plain():
    r"""Tests for Reports.weekly_report_plain

        >>> from datetime import datetime, time
        >>> from gtimelog.timelog import Reports

        >>> vm = time(2, 0)
        >>> min = datetime(2010, 1, 25)
        >>> max = datetime(2010, 1, 31)

        >>> window = make_time_window(StringIO(), min, max, vm)
        >>> reports = Reports(window)
        >>> reports.weekly_report_plain(sys.stdout, 'foo@bar.com', 'Bob Jones')
        To: foo@bar.com
        Subject: Weekly report for Bob Jones (week 04)
        <BLANKLINE>
        No work done this week.

        >>> fh = StringIO('\n'.join([
        ...    '2010-01-30 09:00: start',
        ...    '2010-01-30 09:23: Bing: stuff',
        ...    '2010-01-30 12:54: Bong: other stuff',
        ...    '2010-01-30 13:32: lunch **',
        ...    '2010-01-30 15:46: misc',
        ...    '']))

        >>> window = make_time_window(fh, min, max, vm)
        >>> reports = Reports(window)
        >>> reports.weekly_report_plain(sys.stdout, 'foo@bar.com', 'Bob Jones')
        To: foo@bar.com
        Subject: Weekly report for Bob Jones (week 04)
        <BLANKLINE>
                                                                        time
        Bing: stuff                                                     23 min
        Bong: other stuff                                               3 hours 31 min
        Misc                                                            2 hours 14 min
        <BLANKLINE>
        Total work done this week: 6 hours 8 min
        <BLANKLINE>
        By category:
        <BLANKLINE>
        Bing                                                            23 min
        Bong                                                            3 hours 31 min
        (none)                                                          2 hours 14 min
        <BLANKLINE>

    """


def doctest_Reports_monthly_report_plain():
    r"""Tests for Reports.monthly_report_plain

        >>> from datetime import datetime, time
        >>> from gtimelog.timelog import Reports

        >>> vm = time(2, 0)
        >>> min = datetime(2007, 9, 1)
        >>> max = datetime(2007, 10, 1)

        >>> window = make_time_window(StringIO(), min, max, vm)
        >>> reports = Reports(window)
        >>> reports.monthly_report_plain(sys.stdout, 'foo@bar.com', 'Bob Jones')
        To: foo@bar.com
        Subject: Monthly report for Bob Jones (2007/09)
        <BLANKLINE>
        No work done this month.

        >>> fh = StringIO('\n'.join([
        ...    '2007-09-30 09:00: start',
        ...    '2007-09-30 09:23: Bing: stuff',
        ...    '2007-09-30 12:54: Bong: other stuff',
        ...    '2007-09-30 13:32: lunch **',
        ...    '2007-09-30 15:46: misc',
        ...    '']))

        >>> window = make_time_window(fh, min, max, vm)
        >>> reports = Reports(window)
        >>> reports.monthly_report_plain(sys.stdout, 'foo@bar.com', 'Bob Jones')
        To: foo@bar.com
        Subject: Monthly report for Bob Jones (2007/09)
        <BLANKLINE>
                                                                       time
        Bing: stuff                                                     23 min
        Bong: other stuff                                               3 hours 31 min
        Misc                                                            2 hours 14 min
        <BLANKLINE>
        Total work done this month: 6 hours 8 min
        <BLANKLINE>
        By category:
        <BLANKLINE>
        Bing                                                            23 min
        Bong                                                            3 hours 31 min
        (none)                                                          2 hours 14 min
        <BLANKLINE>

    """


def doctest_Reports_custom_range_report_categorized():
    r"""Tests for Reports.custom_range_report_categorized

        >>> from datetime import datetime, time
        >>> from gtimelog.timelog import Reports

        >>> vm = time(2, 0)
        >>> min = datetime(2010, 1, 25)
        >>> max = datetime(2010, 2, 1)

        >>> window = make_time_window(StringIO(), min, max, vm)
        >>> reports = Reports(window)
        >>> reports.custom_range_report_categorized(sys.stdout, 'foo@bar.com',
        ...                                         'Bob Jones')
        To: foo@bar.com
        Subject: Custom date range report for Bob Jones (2010-01-25 - 2010-01-31)
        <BLANKLINE>
        No work done this custom range.

        >>> fh = StringIO('\n'.join([
        ...    '2010-01-20 09:00: arrived',
        ...    '2010-01-20 09:30: asdf',
        ...    '2010-01-20 10:00: Bar: Foo',
        ...    ''
        ...    '2010-01-30 09:00: arrived',
        ...    '2010-01-30 09:23: Bing: stuff',
        ...    '2010-01-30 12:54: Bong: other stuff',
        ...    '2010-01-30 13:32: lunch **',
        ...    '2010-01-30 23:46: misc',
        ...    '']))

        >>> window = make_time_window(fh, min, max, vm)
        >>> reports = Reports(window)
        >>> reports.custom_range_report_categorized(sys.stdout, 'foo@bar.com',
        ...                                         'Bob Jones')
        To: foo@bar.com
        Subject: Custom date range report for Bob Jones (2010-01-25 - 2010-01-31)
        <BLANKLINE>
                                                                          time
        Bing:
          Stuff                                                           0:23
        ----------------------------------------------------------------------
                                                                          0:23
        <BLANKLINE>
        Bong:
          Other stuff                                                     3:31
        ----------------------------------------------------------------------
                                                                          3:31
        <BLANKLINE>
        No category:
          Misc                                                           10:14
        ----------------------------------------------------------------------
                                                                         10:14
        <BLANKLINE>
        Total work done this custom range: 14:08
        <BLANKLINE>
        Categories by time spent:
          No category     10:14
          Bong             3:31
          Bing             0:23

    """


def doctest_TaskList_missing_file():
    """Test for TaskList

        >>> from gtimelog.timelog import TaskList
        >>> tasklist = TaskList('/nosuchfile')
        >>> tasklist.check_reload()
        False
        >>> tasklist.reload()

    """


def doctest_TaskList_real_file():
    r"""Test for TaskList

        >>> import time
        >>> tempdir = tempfile.mkdtemp(prefix='gtimelog-test-')
        >>> taskfile = os.path.join(tempdir, 'tasks.txt')
        >>> with open(taskfile, 'w') as f:
        ...     _ = f.write('\n'.join([
        ...         '# comments are skipped',
        ...         'some task',
        ...         'other task',
        ...         'project: do it',
        ...         'project: fix bugs',
        ...         'misc: paperwork',
        ...         ]) + '\n')
        >>> one_second_ago = time.time() - 2
        >>> os.utime(taskfile, (one_second_ago, one_second_ago))

        >>> from gtimelog.timelog import TaskList
        >>> tasklist = TaskList(taskfile)
        >>> pprint(tasklist.groups)
        [('Other', ['some task', 'other task']),
         ('misc', ['paperwork']),
         ('project', ['do it', 'fix bugs'])]

        >>> tasklist.check_reload()
        False

        >>> with open(taskfile, 'w') as f:
        ...     _ = f.write('new tasks\n')

        >>> tasklist.check_reload()
        True

        >>> pprint(tasklist.groups)
        [('Other', ['new tasks'])]

        >>> shutil.rmtree(tempdir)

    """


class TestTimeLog(unittest.TestCase):

    def setUp(self):
        self.tempdir = None

    def tearDown(self):
        if self.tempdir:
            shutil.rmtree(self.tempdir)

    def mkdtemp(self):
        if self.tempdir is None:
            self.tempdir = tempfile.mkdtemp(prefix='gtimelog-test-')
        return self.tempdir

    def test_appending_clears_window_cache(self):
        # Regression test for https://github.com/gtimelog/gtimelog/issues/28
        tempfile = os.path.join(self.mkdtemp(), 'timelog.txt')
        timelog = TimeLog(tempfile, datetime.time(2, 0))

        w = timelog.window_for_day(datetime.date(2014, 11, 12))
        self.assertEqual(list(w.all_entries()), [])

        timelog.append('started **', now=datetime.datetime(2014, 11, 12, 10, 00))
        w = timelog.window_for_day(datetime.date(2014, 11, 12))
        self.assertEqual(len(list(w.all_entries())), 1)

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_valid_time_accepts_any_time_in_the_past_when_log_is_empty(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        past = datetime.datetime(2015, 5, 12, 14, 20)
        self.assertTrue(timelog.valid_time(past))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_valid_time_rejects_times_in_the_future(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        future = datetime.datetime(2015, 5, 12, 16, 30)
        self.assertFalse(timelog.valid_time(future))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_valid_time_rejects_times_before_last_entry(self):
        timelog = TimeLog(StringIO("2015-05-12 15:00: did stuff"),
                          datetime.time(2, 0))
        past = datetime.datetime(2015, 5, 12, 14, 20)
        self.assertFalse(timelog.valid_time(past))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_valid_time_accepts_times_between_last_entry_and_now(self):
        timelog = TimeLog(StringIO("2015-05-12 15:00: did stuff"),
                          datetime.time(2, 0))
        past = datetime.datetime(2015, 5, 12, 15, 20)
        self.assertTrue(timelog.valid_time(past))

    def test_parse_correction_leaves_regular_text_alone(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("did stuff"),
                         ("did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_recognizes_absolute_times(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("15:20 did stuff"),
                         ("did stuff", datetime.datetime(2015, 5, 12, 15, 20)))

    @freezegun.freeze_time("2015-05-13 00:27")
    def test_parse_correction_handles_virtual_midnight_yesterdays_time(self):
        # Regression test for https://github.com/gtimelog/gtimelog/issues/33
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("15:20 did stuff"),
                         ("did stuff", datetime.datetime(2015, 5, 12, 15, 20)))

    @freezegun.freeze_time("2015-05-13 00:27")
    def test_parse_correction_handles_virtual_midnight_todays_time(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("00:15 did stuff"),
                         ("did stuff", datetime.datetime(2015, 5, 13, 00, 15)))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_future_absolute_times(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("17:20 did stuff"),
                         ("17:20 did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_bad_absolute_times(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("19:60 did stuff"),
                         ("19:60 did stuff", None))
        self.assertEqual(timelog.parse_correction("24:00 did stuff"),
                         ("24:00 did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_absolute_times_before_last_entry(self):
        timelog = TimeLog(StringIO("2015-05-12 16:00: stuff"),
                          datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("15:20 did stuff"),
                         ("15:20 did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_recognizes_relative_times(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("-20 did stuff"),
                         ("did stuff", datetime.datetime(2015, 5, 12, 16, 7)))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_relative_times_before_last_entry(self):
        timelog = TimeLog(StringIO("2015-05-12 16:00: stuff"),
                          datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("-30 did stuff"),
                         ("-30 did stuff", None))

    @freezegun.freeze_time("2015-05-12 16:27")
    def test_parse_correction_ignores_bad_relative_times(self):
        timelog = TimeLog(StringIO(), datetime.time(2, 0))
        self.assertEqual(timelog.parse_correction("-200 did stuff"),
                         ("-200 did stuff", None))


class TestTagging(unittest.TestCase):

    TEST_TIMELOG = textwrap.dedent("""
        2014-05-27 10:03: arrived
        2014-05-27 10:13: edx: introduce topic to new sysadmins -- edx
        2014-05-27 10:30: email
        2014-05-27 12:11: meeting: how to support new courses?  -- edx meeting
        2014-05-27 15:12: edx: write test procedure for EdX instances -- edx sysadmin
        2014-05-27 17:03: cluster: set-up accounts, etc. -- sysadmin hpc
        2014-05-27 17:14: support: how to run statistics on Hydra? -- support hydra
        2014-05-27 17:36: off: pause **
        2014-05-27 17:38: email
        2014-05-27 19:06: off: dinner & family **
        2014-05-27 22:19: cluster: fix shmmax-shmall issue -- sysadmin hpc
        """)

    def setUp(self):
        self.tw = make_time_window(
            StringIO(self.TEST_TIMELOG),
            datetime.datetime(2014, 5, 27, 9, 0),
            datetime.datetime(2014, 5, 27, 23, 59),
            datetime.time(2, 0),
        )

    def test_TimeWindow_set_of_all_tags(self):
        tags = self.tw.set_of_all_tags()
        self.assertEqual(tags, {'edx', 'hpc', 'hydra', 'meeting',
                                'support', 'sysadmin'})

    def test_TimeWindow_totals_per_tag1(self):
        """Test aggregate time per tag, 1 entry only"""
        result = self.tw.totals('meeting')
        self.assertEqual(len(result), 2)
        work, slack = result
        self.assertEqual(work,
            # start/end times are manually extracted from the TEST_TIMELOG sample
            (datetime.timedelta(hours=12, minutes=11) - datetime.timedelta(hours=10, minutes=30))
        )
        self.assertEqual(slack, datetime.timedelta(0))

    def test_TimeWindow_totals_per_tag2(self):
        """Test aggregate time per tag, several entries"""
        result = self.tw.totals('hpc')
        self.assertEqual(len(result), 2)
        work, slack = result
        self.assertEqual(work,
            # start/end times are manually extracted from the TEST_TIMELOG sample
            (datetime.timedelta(hours=17, minutes=3) - datetime.timedelta(hours=15, minutes=12))
            + (datetime.timedelta(hours=22, minutes=19) - datetime.timedelta(hours=19, minutes=6))
        )
        self.assertEqual(slack, datetime.timedelta(0))

    def test_TimeWindow__split_entry_and_tags1(self):
        """Test `TimeWindow._split_entry_and_tags` with simple entry"""
        result = self.tw._split_entry_and_tags('email')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'email')
        self.assertEqual(result[1], set())

    def test_TimeWindow__split_entry_and_tags2(self):
        """Test `TimeWindow._split_entry_and_tags` with simple entry and tags"""
        result = self.tw._split_entry_and_tags('restart CFEngine server -- sysadmin cfengine issue327')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'restart CFEngine server')
        self.assertEqual(result[1], {'sysadmin', 'cfengine', 'issue327'})

    def test_TimeWindow__split_entry_and_tags3(self):
        """Test `TimeWindow._split_entry_and_tags` with category, entry, and tags"""
        result = self.tw._split_entry_and_tags('tooling: tagging support in gtimelog -- tooling gtimelog')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'tooling: tagging support in gtimelog')
        self.assertEqual(result[1], {'tooling', 'gtimelog'})

    def test_TimeWindow__split_entry_and_tags4(self):
        """Test `TimeWindow._split_entry_and_tags` with slack-type entry"""
        result = self.tw._split_entry_and_tags('read news -- reading **')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'read news **')
        self.assertEqual(result[1], {'reading'})

    def test_TimeWindow__split_entry_and_tags5(self):
        """Test `TimeWindow._split_entry_and_tags` with slack-type entry"""
        result = self.tw._split_entry_and_tags('read news -- reading ***')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'read news ***')
        self.assertEqual(result[1], {'reading'})

    def test_Reports__report_tags(self):
        from gtimelog.timelog import Reports
        rp = Reports(self.tw)
        txt = StringIO()
        # use same tags as in tests above, so we know the totals
        rp._report_tags(txt, ['meeting', 'hpc'])
        self.assertEqual(
            txt.getvalue().strip(),
            textwrap.dedent("""
            Time spent in each area:

              hpc          5:04
              meeting      1:41

            Note that area totals may not add up to the period totals,
            as each entry may be belong to multiple areas (or none at all).
            """).strip())


def additional_tests(): # for setup.py
    return doctest.DocTestSuite(optionflags=doctest.NORMALIZE_WHITESPACE,
                                checker=Checker())


def test_suite():
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromName(__name__),
        additional_tests(),
    ])