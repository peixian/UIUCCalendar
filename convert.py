#!/usr/bin/python
# Ryan Hitchman, 2011
# public domain under CC0 / WTFPL

import logging
import os
import traceback
from datetime import datetime


def hour_from_ampm(hour, ispm):
    # why can't python's strptime just implement %p properly?
    # working with dates: completely terrible in every language
    if hour == 12:
        if not ispm:
            hour = 0
    elif ispm:
        return hour + 12
    return hour


def date_time_to_timestamp(date, clock):
    # ("Jan 27, 2011", "8:00 pm") -> "20110127T200000"
    t = datetime.strptime(date.strip(), "%b %d, %Y")
    c = datetime.strptime(clock.strip(), "%H:%M %p")

    t = t.replace(hour=hour_from_ampm(c.hour, 'pm' in clock), minute=c.minute)

    return datetime.strftime(t, "%Y%m%dT%H%M%S")


def parse_class(line):
    split = line.split('\t')
    if len(split) != 12:
        return

    split = [s.strip() for s in split]

    (crn, course, title, campus, credits, level, 
            start, end, days, time, location, instructor) = split

    if time in ('TBA', 'Time') or not time:
        # skip classes with no scheduled times
        return
    
    title = title.replace("&amp;", "&")

    time_begin, time_end = time.split('-')
    time_begin = date_time_to_timestamp(start, time_begin)
    time_end = date_time_to_timestamp(start, time_end)
    class_end = date_time_to_timestamp(end, "11:59 pm")

    # convert things like "MWF" -> "MO,WE,FR"
    for pair in ('M MO', 'T TU', 'W WE', 'R TH', 'F FR'):
        one, two = pair.split()
        days = days.replace(one, two + ',')

    days = days.rstrip(' ,')

    if course:
        course, section = course.rsplit(' ', 1)
    else:
        section = ''

    return dict(crn=crn, course=course, section=section, title=title,
        campus=campus, credits=credits, level=level, 
        start=start, end=end, days=days, time=time,
        time_begin=time_begin, time_end=time_end, class_end=class_end,
        location=location, instructor=instructor)


def parse_schedule(text):
    has_debugged = False

    classes = []
    
    for line in text.splitlines():
        try:
            cls = parse_class(line)
            if cls is not None:
                if not cls['course'].strip(): # for classes with multiple time,
                    # subsequent lines don't include a lot of the information,
                    # so fill it in using the previous class
                    prevcls = classes[-1]
                    for key in 'crn course section title campus credits level'.split():
                        cls[key] = prevcls[key]

                classes.append(cls)
        except Exception:
            if not has_debugged:
                logging.debug(text)
                has_debugged = True
            logging.warning(traceback.format_exc())

    if not classes and not has_debugged:
        logging.debug(text)

    return classes

if __name__ == "__main__":
    import sys
    print parse_schedule(unicode(sys.stdin.read()))

'''
Django template for formatting calendars using the output of parse_schedule:

BEGIN:VCALENDAR
PRODID:-//Ryan Hitchman//UIUC Calendar//EN
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:UIUC Classes
X-WR-TIMEZONE:America/Chicago
X-WR-CALDESC:Classes taken at UIUC
{% for c in classes %}
BEGIN:VEVENT
SUMMARY:{{c.course}} - {{c.title}} {{c.section}}
LOCATION:{{c.location}} 
DESCRIPTION:{{c.section}} - {{c.instructor}}\nCRN: {{c.crn}}
DTSTART;TZID=America/Chicago:{{c.time_begin}}
DTEND;TZID=America/Chicago:{{c.time_end}}
RRULE:FREQ=WEEKLY;WKST=MO;UNTIL={{c.class_end}};BYDAY={{c.days}}
TRANSP:OPAQUE
END:VEVENT
{% endfor %}
END:VCALENDAR
'''