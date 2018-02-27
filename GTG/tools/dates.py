# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

""" General class for representing dates in GTG.

Dates Could be normal like 2012-04-01 or fuzzy like now, soon,
someday, later or no date.

Date.parse() parses all possible representations of a date. """

import calendar
import datetime
import locale
import re

from GTG import _, ngettext

__all__ = 'Date',

ASAP, NOW, NEXT, SOONER, SOON, SOONISH, LATER, SOMEDAY, NODATE = range(9)
# strings representing fuzzy dates + no date
ENGLISH_STRINGS = {
    ASAP: 'asap',
    NOW: 'now',
    NEXT:    'next',
    SOONER:  'sooner',
    SOON: 'soon',
    SOONISH: 'soonish',
    LATER:   'later',
    SOMEDAY: 'someday',
    NODATE: '',
}

STRINGS = {
    ASAP: _('asap'),
    NOW: _('now'),
    NEXT:    _('next'),
    SOONER:  _('sooner'),
    SOON: _('soon'),
    SOONISH: _('soonish'),
    LATER:   _('later'),
    SOMEDAY: _('someday'),
    NODATE: '',
}

LOOKUP = {
    'asap'   : ASAP   , _('asap'   ).lower(): ASAP,
    'now'    : NOW    , _('now'    ).lower(): NOW,
    'next'   : NEXT   , _('next'   ).lower(): NEXT,
    'sooner' : SOONER , _('sooner' ).lower(): SOONER,
    'soon'   : SOON   , _('soon'   ).lower(): SOON,
    'soonish': SOONISH, _('soonish').lower(): SOONISH,
    'later'  : LATER  , _('later'  ).lower(): LATER,
    'someday': SOMEDAY, _('someday').lower(): SOMEDAY,
    '': NODATE,
}

# ISO 8601 date format
ISODATE = '%Y-%m-%d'
# get date format from locale
locale_format = locale.nl_langinfo(locale.D_FMT)


def convert_datetime_to_date(aday):
    """ Convert python's datetime to date.
    Strip unusable time information. """
    return datetime.date(aday.year, aday.month, aday.day)


class Date(object):
    """A date class that supports fuzzy dates.

    Date supports all the methods of the standard datetime.date class. A Date
    can be constructed with:
      - the fuzzy strings 'now', 'soon', '' (no date, default), or 'someday'
      - a string containing an ISO format date: YYYY-MM-DD, or
      - a datetime.date or Date instance, or
      - a string containing a locale format date.
    """
    _real_date = None
    _fuzzy = None

    def __init__(self, value=''):
        self._parse_init_value(value)

    def _parse_init_value(self, value):
        """ Parse many possible values and setup date """
        if value is None:
            self._parse_init_value(NODATE)
        elif isinstance(value, datetime.date):
            self._real_date = value
        elif isinstance(value, Date):
            # Copy internal values from other Date object
            self._real_date = value._real_date
            self._fuzzy = value._fuzzy
        elif isinstance(value, str) or isinstance(value, unicode):
            try:
                da_ti = datetime.datetime.strptime(value, locale_format).date()
                self._real_date = convert_datetime_to_date(da_ti)
            except ValueError:
                try:
                    # allow both locale format and ISO format
                    da_ti = datetime.datetime.strptime(value, ISODATE).date()
                    self._real_date = convert_datetime_to_date(da_ti)
                except ValueError:
                    # it must be a fuzzy date
                    try:
                        value = str(value.lower())
                        self._parse_init_value(LOOKUP[value])
                    except KeyError:
                        raise ValueError("Unknown value for date: '%s'"
                                         % value)
        elif isinstance(value, int):
            self._fuzzy = value
        else:
            raise ValueError("Unknown value for date: '%s'" % value)

    def date(self):
        """ Map date into real date, i.e. convert fuzzy dates """
        if self.is_fuzzy():
            # More expensive than it needs to be...
            # Originally, "NOW" was today (which makes logical sense) and "NEXT"
            # was set as "Tomorrow" (+1; the minimal increment), but after having
            # so many tasks overdue, due "today", and "now"... approaching deadlines
            # are too easily missed until we are right on top of them. So until such
            # a time as a full estimation system is in place, we'll try for a smoother
            # & more predictable fuzzy date spread (rather than a wholly logical one).
            daysTillNext=5;
            FUNCS = {
                ASAP   : datetime.date.min,
                NOW    : datetime.date.today(),
                NEXT   : datetime.date.today() + datetime.timedelta(daysTillNext),
                SOONER : datetime.date.today() + datetime.timedelta(daysTillNext*2),
                SOON   : datetime.date.today() + datetime.timedelta(daysTillNext*3),
                SOONISH: datetime.date.today() + datetime.timedelta(daysTillNext*4),
                NODATE : datetime.date.max - datetime.timedelta(2),
                LATER  : datetime.date.max - datetime.timedelta(1),
                SOMEDAY: datetime.date.max,
            }
            return FUNCS[self._fuzzy]
        else:
            return self._real_date

    def __add__(self, other):
        if isinstance(other, datetime.timedelta):
            return Date(self.date() + other)
        else:
            raise NotImplementedError
    __radd__ = __add__

    def __sub__(self, other):
        if hasattr(other, 'date'):
            return self.date() - other.date()
        else:
            return self.date() - other

    def __rsub__(self, other):
        if hasattr(other, 'date'):
            return other.date() - self.date()
        else:
            return other - self.date()

    def __cmp__(self, other):
        """ Compare with other Date instance """
        if isinstance(other, Date):
            comparison = cmp(self.date(), other.date())

            # Keep fuzzy dates below normal dates
            if comparison == 0:
                if self.is_fuzzy() and not other.is_fuzzy():
                    return 1
                elif not self.is_fuzzy() and other.is_fuzzy():
                    return -1

            return comparison
        elif isinstance(other, datetime.date):
            return cmp(self.date(), other)
        else:
            raise NotImplementedError

    def __str__(self):
        if self._fuzzy is not None:
            return STRINGS[self._fuzzy]
        else:
            return self._real_date.isoformat()

    def __repr__(self):
        return "GTG_Date(%s)" % str(self)

    def xml_str(self):
        """ Representation for XML - fuzzy dates are in English """
        if self._fuzzy is not None:
            return ENGLISH_STRINGS[self._fuzzy]
        else:
            return self._real_date.isoformat()

    def __nonzero__(self):
        return self._fuzzy != NODATE

    def __getattr__(self, name):
        """ Provide access to the wrapped datetime.date """
        try:
            return self.__dict__[name]
        except KeyError:
            return getattr(self.date(), name)

    def is_fuzzy(self):
        """
        True if the Date is one of the fuzzy values:
        now, soon, someday or no_date
        """
        return self._fuzzy is not None

    def days_left(self):
        """ Return the difference between the date and today in dates """
        if self._fuzzy == NODATE:
            return None
        else:
            return (self.date() - datetime.date.today()).days

    @classmethod
    def today(cls):
        """ Return date for today """
        return Date(datetime.date.today())

    @classmethod
    def tomorrow(cls):
        """ Return date for tomorrow """
        return Date(datetime.date.today() + datetime.timedelta(1))

    @classmethod
    def asap(cls):
        """ Return date representing fuzzy date: asap """
        return Date(ASAP)

    @classmethod
    def now(cls):
        """ Return date representing fuzzy date now """
        return Date(NOW)

    @classmethod
    def next(cls):
        """ Return date representing fuzzy date next """
        return Date(NEXT)

    @classmethod
    def no_date(cls):
        """ Return date representing no (set) date """
        return Date(NODATE)

    @classmethod
    def sooner(cls):
        """ Return date representing fuzzy date sooner """
        return Date(SOONER)

    @classmethod
    def soon(cls):
        """ Return date representing fuzzy date soon """
        return Date(SOON)

    @classmethod
    def soonish(cls):
        """ Return date representing fuzzy date soonish """
        return Date(SOONISH)

    @classmethod
    def later(cls):
        """ Return date representing fuzzy date later """
        return Date(LATER)

    @classmethod
    def someday(cls):
        """ Return date representing fuzzy date someday """
        return Date(SOMEDAY)

    @classmethod
    def _parse_only_month_day(cls, string):
        """ Parse next Xth day in month """
        try:
            mday = int(string)
            if not 1 <= mday <= 31 or string.startswith('0'):
                return None
        except ValueError:
            return None

        today = datetime.date.today()
        try:
            result = today.replace(day=mday)
        except ValueError:
            result = None

        if result is None or result <= today:
            if today.month == 12:
                next_month = 1
                next_year = today.year + 1
            else:
                next_month = today.month + 1
                next_year = today.year

            try:
                result = datetime.date(next_year, next_month, mday)
            except ValueError:
                pass

        return result

    @classmethod
    def _parse_numerical_format(cls, string):
        """ Parse numerical formats like %Y/%m/%d, %Y%m%d or %m%d """
        result = None
        today = datetime.date.today()
        for fmt in ['%Y/%m/%d', '%Y%m%d', '%m%d']:
            try:
                da_ti = datetime.datetime.strptime(string, fmt)
                result = convert_datetime_to_date(da_ti)
                if '%Y' not in fmt:
                    # If the day has passed, assume the next year
                    if result.month > today.month or \
                        (result.month == today.month and
                         result.day >= today.day):
                        year = today.year
                    else:
                        year = today.year + 1
                    result = result.replace(year=year)
            except ValueError:
                continue
        return result

    @classmethod
    def _parse_text_representation(cls, string):
        """ Match common text representation for date """

        today = datetime.date.today()
        inverter = 1;

        # BUG: mostly english-centric.
        # TODO: consider using 'timestring' as the core date parser (wrong values for negatives or week/month qualifiers).
        if string.startswith('-'):
            inverter=-1;
            string=string[1:];

        if string.startswith('+'):
            string=string[1:];

        if string.endswith(' ago'):
            inverter=-1;
            string=string[:-4];

        if string.endswith(' from now'):
            string=string[:-9];

        # Did they just specify a number of days?
        if string.isdigit():
            return today + datetime.timedelta(int(string)*inverter);

        numericPart=re.sub('[^0-9]', '', string);

        if numericPart:
            if string.endswith('d') or 'day' in string:
                return today + datetime.timedelta(int(numericPart)*inverter);
            if string.endswith('w') or 'week' in string:
                return today + datetime.timedelta(int(numericPart)*7*inverter);
            if string.endswith('m') or 'month' in string:
                return today + datetime.timedelta(int(numericPart)*30*inverter);
            if string.endswith('y') or 'year' in string:
                return today + datetime.timedelta(int(numericPart)*365*inverter);
            print "WARN: likely not understanding numeric qualifiers: "+string;

        # NB: Hereafter is mostly upstream, and supports localization.

        formats = {
            'yday': -1,
            _('yesterday').lower(): -1,
            'today': 0,
            _('today').lower(): 0,
            'tomorrow': 1,
            _('tomorrow').lower(): 1,
            'next week': 7,
            _('next week').lower(): 7,
            'next month': calendar.mdays[today.month],
            _('next month').lower(): calendar.mdays[today.month],
            'next year': 365 + int(calendar.isleap(today.year)),
            _('next year').lower(): 365 + int(calendar.isleap(today.year)),
        }

        # If they just type a day name, assume it is in the future
        for i, (english, local) in enumerate([
            ("Monday"   , _("Monday")),
            ("Tuesday"  , _("Tuesday")),
            ("Wednesday", _("Wednesday")),
            ("Thursday" , _("Thursday")),
            ("Friday"   , _("Friday")),
            ("Saturday" , _("Saturday")),
            ("Sunday"   , _("Sunday")),
        ]):
            offset = i - today.weekday() + 7 * int(i <= today.weekday())
            formats[english.lower()] = offset
            formats[local.lower()] = offset

        # But if they say 'next X' and 'X' already would be in the future, add a week.
        for i, (english, local) in enumerate([
            ("Next Monday"   , _("Next Monday")),
            ("Next Tuesday"  , _("Next Tuesday")),
            ("Next Wednesday", _("Next Wednesday")),
            ("Next Thursday" , _("Next Thursday")),
            ("Next Friday"   , _("Next Friday")),
            ("Next Saturday" , _("Next Saturday")),
            ("Next Sunday"   , _("Next Sunday")),
        ]):
            offset = i - today.weekday() + 7 * int(i <= today.weekday()) + (7 if i> today.weekday() else 0)
            formats[english.lower()] = offset
            formats[local.lower()] = offset

        # ...and 'last X' implies the past, of course.
        for i, (english, local) in enumerate([
            ("Last Monday"   , _("Last Monday")),
            ("Last Tuesday"  , _("Last Tuesday")),
            ("Last Wednesday", _("Last Wednesday")),
            ("Last Thursday" , _("Last Thursday")),
            ("Last Friday"   , _("Last Friday")),
            ("Last Saturday" , _("Last Saturday")),
            ("Last Sunday"   , _("Last Sunday")),
        ]):
            offset = i - today.weekday() + 7 * int(i <= today.weekday()) - (7 if i> today.weekday() else 0)
            formats[english.lower()] = offset
            formats[local.lower()] = offset

        offset = formats.get(string, None)
        if offset is None:
            return None
        else:
            return today + datetime.timedelta(offset)

    @classmethod
    def parse(cls, string):
        """Return a Date corresponding to string, or None.

        string may be in one of the following formats:
            - YYYY/MM/DD, YYYYMMDD, MMDD, D
            - fuzzy dates
            - 'today', 'tomorrow', 'next week', 'next month' or 'next year' in
                English or the system locale.
        """
        # sanitize input
        if string is None:
            string = ''
        else:
            string = string.lower()

        # try the default formats
        try:
            return Date(string)
        except ValueError:
            pass

        # do several parsing
        result = cls._parse_only_month_day(string)
        if result is None:
            result = cls._parse_numerical_format(string)
        if result is None:
            result = cls._parse_text_representation(string)

        # Announce the result
        if result is not None:
            return Date(result)
        else:
            raise ValueError("Can't parse date '%s'" % string)

    def to_readable_string(self):
        """ Return nice representation of date.

        Fuzzy dates => localized version
        Close dates => Today, Tomorrow, In X days
        Other => with locale dateformat, stripping year for this year
        """
        if self._fuzzy is not None:
            return STRINGS[self._fuzzy]

        days_left = self.days_left()
        if days_left == 0:
            return _('Today')
        elif days_left < 0:
            abs_days = abs(days_left)
            return ngettext('Yesterday', '%(days)d days ago', abs_days) % \
                {'days': abs_days}
        elif days_left > 0 and days_left <= 15:
            return ngettext('Tomorrow', 'In %(days)d days', days_left) % \
                {'days': days_left}
        else:
            locale_format = locale.nl_langinfo(locale.D_FMT)
            if calendar.isleap(datetime.date.today().year):
                year_len = 366
            else:
                year_len = 365
            if float(days_left) / year_len < 1.0:
                # if it's in less than a year, don't show the year field
                locale_format = locale_format.replace('/%Y', '')
                locale_format = locale_format.replace('.%Y', '.')
            return self._real_date.strftime(locale_format)
