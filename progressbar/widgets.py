#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# progressbar  - Text progress bar library for Python.
# Copyright (c) 2005 Nilton Volpato
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''Default ProgressBar widgets'''

from __future__ import division, absolute_import, with_statement

import datetime
import math
import abc
import sys
import pprint

from . import utils


class FormatWidgetMixin(object):
    '''Mixin to format widgets using a formatstring

    Variables available:
     - max_value: The maximum value (can be None with iterators)
     - value: The current value
     - total_seconds_elapsed: The seconds since the bar started
     - seconds_elapsed: The seconds since the bar started modulo 60
     - minutes_elapsed: The minutes since the bar started modulo 60
     - hours_elapsed: The hours since the bar started modulo 24
     - days_elapsed: The hours since the bar started
     - time_elapsed: Shortcut for HH:MM:SS time since the bar started including
       days
     - percentage: Percentage as a float
    '''
    required_values = []

    def __init__(self, format):
        self.format = format
        super(FormatWidgetMixin, self).__init__()

    def __call__(self, progress, data):
        '''Formats the widget into a string'''
        try:
            return self.format % data
        except (TypeError, KeyError):
            print >> sys.stderr, 'Error while formatting %r' % self.format
            pprint.pprint(data, stream=sys.stderr)
            raise


class WidgetBase(object):
    __metaclass__ = abc.ABCMeta
    '''The base class for all widgets

    The ProgressBar will call the widget's update value when the widget should
    be updated. The widget's size may change between calls, but the widget may
    display incorrectly if the size changes drastically and repeatedly.

    The boolean TIME_SENSITIVE informs the ProgressBar that it should be
    updated more often because it is time sensitive.

    WARNING: Widgets can be shared between multiple progressbars so any state
    information specific to a progressbar should be stored within the
    progressbar instead of the widget.
    '''
    INTERVAL = None

    @abc.abstractmethod
    def __call__(self, progress, data):
        '''Updates the widget.

        progress - a reference to the calling ProgressBar
        '''


class AutoWidthWidgetBase(WidgetBase):
    '''The base class for all variable width widgets.

    This widget is much like the \\hfill command in TeX, it will expand to
    fill the line. You can use more than one in the same line, and they will
    all have the same width, and together will fill the line.
    '''

    @abc.abstractmethod
    def __call__(self, progress, data, width):
        '''Updates the widget providing the total width the widget must fill.

        progress - a reference to the calling ProgressBar
        width - The total width the widget must fill
        '''


class TimeSensitiveWidgetBase(WidgetBase):
    '''The base class for all time sensitive widgets.

    Some widgets like timers would become out of date unless updated at least
    every `INTERVAL`
    '''
    INTERVAL = datetime.timedelta(seconds=1)


class Timer(FormatWidgetMixin, TimeSensitiveWidgetBase):
    '''WidgetBase which displays the elapsed seconds.'''

    def __init__(self, format='Elapsed Time: %(time_elapsed)s'):
        super(Timer, self).__init__(format=format)

    @staticmethod
    def format_time(seconds):
        '''Formats time as the string "HH:MM:SS".'''
        return str(datetime.timedelta(seconds=int(seconds)))


class SamplesMixin(object):
    def __init__(self, samples=10, key_prefix=None):
        self.samples = samples
        self.key_prefix = (self.__class__.__name__ or key_prefix) + '_'

    def get_sample_times(self, progress, data):
        return progress.extra.setdefault(self.key_prefix + 'sample_times', [])

    def get_sample_values(self, progress, data):
        return progress.extra.setdefault(self.key_prefix + 'sample_values', [])

    def __call__(self, progress, data):
        sample_times = self.get_sample_times(progress, data)
        sample_values = self.get_sample_values(progress, data)

        if progress.value != progress.previous_value:
            # Add a sample but limit the size to `num_samples`
            sample_times.append(progress.last_update_time)
            sample_values.append(progress.value)

            if len(sample_times) > self.samples:
                sample_times.pop(0)
                sample_values.pop(0)

        return sample_times, sample_values


class ETA(Timer):
    '''WidgetBase which attempts to estimate the time of arrival.'''

    def _eta(self, progress, data, value, elapsed):
        if value == progress.min_value:
            return 'ETA:  --:--:--'
        elif progress.end_time:
            return 'Time: %s' % elapsed
        else:
            eta = elapsed * progress.max_value / value - elapsed
            return 'ETA: %s' % self.format_time(eta)

    def __call__(self, progress, data):
        '''Updates the widget to show the ETA or total time when finished.'''
        return self._eta(progress, data, data['value'],
                         data['total_seconds_elapsed'])


class AdaptiveETA(ETA, SamplesMixin):
    '''WidgetBase which attempts to estimate the time of arrival.

    Uses a sampled average of the speed based on the 10 last updates.
    Very convenient for resuming the progress halfway.
    '''

    def __call__(self, progress, data):
        times, values = SamplesMixin.__call__(self, progress, data)

        if len(times) <= 1:
            # No samples so just return the normal ETA calculation
            return ETA.__call__(self, progress, data)
        else:
            return self._eta(progress, data, values[-1] - values[0],
                             utils.timedelta_to_seconds(times[-1] - times[0]))


class FileTransferSpeed(FormatWidgetMixin, TimeSensitiveWidgetBase):
    '''
    WidgetBase for showing the transfer speed (useful for file transfers).
    '''

    def __init__(
            self, format='%(scaled)5.1f %(prefix)s%(unit)-s', unit='B',
            prefixes=('', 'ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi')):
        self.unit = unit
        self.prefixes = prefixes
        super(FileTransferSpeed, self).__init__(format=format)

    def _speed(self, value, elapsed):
        speed = float(value) / elapsed
        power = min(int(math.log(speed, 2) / 10), len(self.prefixes) - 1)
        scaled = speed / (2 ** (10 * power))
        return scaled, power

    def __call__(self, progress, data, value=None, total_seconds_elapsed=None):
        '''Updates the widget with the current SI prefixed speed.'''
        value = data['value'] or value
        elapsed = data['total_seconds_elapsed'] or total_seconds_elapsed

        if elapsed > 2e-6 and value > 2e-6:  # =~ 0
            scaled, power = self._speed(value, elapsed)
        else:
            scaled = power = 0

        data['scaled'] = scaled
        data['prefix'] = self.prefixes[power]
        data['unit'] = self.unit
        return FormatWidgetMixin.__call__(self, progress, data)


class AdaptiveTransferSpeed(FileTransferSpeed, SamplesMixin):
    '''WidgetBase for showing the transfer speed, based on the last X samples
    '''

    def __call__(self, progress, data):
        times, values = SamplesMixin.__call__(self, progress, data)
        if len(times) <= 1:
            # No samples so just return the normal transfer speed calculation
            value = None
            elapsed = None
        else:
            value = values[-1] - values[0]
            elapsed = utils.timedelta_to_seconds(times[-1] - times[0])

        return FileTransferSpeed.__call__(self, progress, data, value, elapsed)


class AnimatedMarker(WidgetBase):

    '''An animated marker for the progress bar which defaults to appear as if
    it were rotating.
    '''

    def __init__(self, markers='|/-\\', default=None):
        self.markers = markers
        self.default = default or markers[0]

    def __call__(self, progress, data, width=None):
        '''Updates the widget to show the next marker or the first marker when
        finished'''

        if progress.end_time:
            return self.default

        return self.markers[data['updates'] % len(self.markers)]

# Alias for backwards compatibility
RotatingMarker = AnimatedMarker


class Counter(FormatWidgetMixin, WidgetBase):

    '''Displays the current count'''

    def __init__(self, format='%(value)d'):
        super(Counter, self).__init__(format=format)


class Percentage(FormatWidgetMixin, WidgetBase):
    '''Displays the current percentage as a number with a percent sign.'''

    def __init__(self, format='%(percentage)3d%%'):
        super(Percentage, self).__init__(format=format)


class FormatLabel(Timer):

    '''Displays a formatted label'''

    mapping = {
        'elapsed': ('seconds_elapsed', Timer.format_time),
        'finished': ('end_time', None),
        'last_update': ('last_update_time', None),
        'max': ('max_value', None),
        'seconds': ('seconds_elapsed', None),
        'start': ('start_time', None),
        'elapsed': ('total_seconds_elapsed', Timer.format_time),
        'value': ('value', None),
    }

    def __init__(self, format):
        self.format = format

    def __call__(self, progress, data):
        for name, (key, transform) in self.mapping.items():
            try:
                if transform is None:
                    data[name] = data[key]
                else:
                    data[name] = transform(data[key])
            except:  # pragma: no cover
                pass

        return FormatWidgetMixin.__call__(self, progress, data)


class SimpleProgress(FormatWidgetMixin, WidgetBase):

    '''Returns progress as a count of the total (e.g.: "5 of 47")'''

    def __init__(self, format='%(value)d of %(max_value)d'):
        super(SimpleProgress, self).__init__(format=format)


class Bar(AutoWidthWidgetBase):

    '''A progress bar which stretches to fill the line.'''
    def __init__(self, marker='#', left='|', right='|', fill=' ',
                 fill_left=True):
        '''Creates a customizable progress bar.

        The callable takes the same parameters as the `__call__` method

        marker - string or callable object to use as a marker
        left - string or callable object to use as a left border
        right - string or callable object to use as a right border
        fill - character to use for the empty part of the progress bar
        fill_left - whether to fill from the left or the right
        '''
        def string_or_lambda(input_):
            if isinstance(input_, basestring):
                return lambda progress, data, width: input_ % data
            else:
                return input_

        def _marker(marker):
            def __marker(progress, data, width):
                if progress.max_value > 0:
                    length = int(progress.value / progress.max_value * width)
                    return (marker * length)
                else:
                    return ''

            if isinstance(marker, basestring):
                assert len(marker) == 1, 'Markers are required to be 1 char'
                return __marker
            else:
                return marker

        self.marker = _marker(marker)
        self.left = string_or_lambda(left)
        self.right = string_or_lambda(right)
        self.fill = string_or_lambda(fill)
        self.fill_left = fill_left

        super(Bar, self).__init__()

    def __call__(self, progress, data, width):
        '''Updates the progress bar and its subcomponents'''

        left = self.left(progress, data, width)
        right = self.right(progress, data, width)
        width -= len(left) + len(right)
        marker = self.marker(progress, data, width)
        fill = self.fill(progress, data, width)

        if self.fill_left:
            marker = marker.ljust(width, fill)
        else:
            marker = marker.rjust(width, fill)

        return left + marker + right


class ReverseBar(Bar):

    '''A bar which has a marker which bounces from side to side.'''

    def __init__(self, marker='#', left='|', right='|', fill=' ',
                 fill_left=False):
        '''Creates a customizable progress bar.

        marker - string or updatable object to use as a marker
        left - string or updatable object to use as a left border
        right - string or updatable object to use as a right border
        fill - character to use for the empty part of the progress bar
        fill_left - whether to fill from the left or the right
        '''
        Bar.__init__(self, marker=marker, left=left, right=right, fill=fill,
                     fill_left=fill_left)


class BouncingBar(Bar):

    def update(self, progress, width):
        '''Updates the progress bar and its subcomponents'''

        left, marker, right = (i for i in (self.left, self.marker, self.right))

        width -= len(left) + len(right)

        if progress.finished:
            return '%s%s%s' % (left, width * marker, right)

        position = int(progress.value % (width * 2 - 1))
        if position > width:
            position = width * 2 - position
        lpad = self.fill * (position - 1)
        rpad = self.fill * (width - len(marker) - len(lpad))

        # Swap if we want to bounce the other way
        if not self.fill_left:
            rpad, lpad = lpad, rpad

        return '%s%s%s%s%s' % (left, lpad, marker, rpad, right)

