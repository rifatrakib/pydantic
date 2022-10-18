import re
from datetime import date, datetime, time, timedelta, timezone

import pytest
from dirty_equals import HasRepr

from pydantic import BaseModel, FutureDate, PastDate, ValidationError, condate

from .conftest import Err


def create_tz(minutes):
    return timezone(timedelta(minutes=minutes))


@pytest.fixture(scope='module', name='DateModel')
def date_model_fixture():
    class DateModel(BaseModel):
        d: date

    return DateModel


@pytest.mark.parametrize(
    'value,result',
    [
        # Valid inputs
        (1_493_942_400, date(2017, 5, 5)),
        (1_493_942_400_000, date(2017, 5, 5)),
        (0, date(1970, 1, 1)),
        ('2012-04-23', date(2012, 4, 23)),
        (b'2012-04-23', date(2012, 4, 23)),
        (date(2012, 4, 9), date(2012, 4, 9)),
        (datetime(2012, 4, 9, 0, 0), date(2012, 4, 9)),
        # Invalid inputs
        (datetime(2012, 4, 9, 12, 15), Err('Datetimes provided to dates should have zero time - e.g. be exact dates')),
        ('x20120423', Err('Input should be a valid date or datetime, input is too short')),
        ('2012-04-56', Err('Input should be a valid date or datetime, day value is outside expected range')),
        (19_999_958_400, date(2603, 10, 11)),  # just before watershed
        (20000044800, Err('kind=date_from_datetime_inexact,')),  # just after watershed
        (1_549_238_400, date(2019, 2, 4)),  # nowish in s
        (1_549_238_400_000, date(2019, 2, 4)),  # nowish in ms
        (1_549_238_400_000_000, Err('Input should be a valid date or datetime, dates after 9999')),  # nowish in μs
        (1_549_238_400_000_000_000, Err('Input should be a valid date or datetime, dates after 9999')),  # nowish in ns
        ('infinity', Err('Input should be a valid date or datetime, input is too short')),
        (float('inf'), Err('Input should be a valid date or datetime, dates after 9999')),
        (int('1' + '0' * 100), Err('Input should be a valid date or datetime, dates after 9999')),
        (1e1000, Err('Input should be a valid date or datetime, dates after 9999')),
        (float('-infinity'), Err('Input should be a valid date or datetime, dates before 1600')),
        (float('nan'), Err('Input should be a valid date or datetime, NaN values not permitted')),
    ],
)
def test_date_parsing(DateModel, value, result):
    if isinstance(result, Err):
        with pytest.raises(ValidationError, match=result.message_escaped()):
            DateModel(d=value)
    else:
        assert DateModel(d=value).d == result


@pytest.fixture(scope='module', name='TimeModel')
def time_model_fixture():
    class TimeModel(BaseModel):
        d: time

    return TimeModel


@pytest.mark.parametrize(
    'value,result',
    [
        # Valid inputs
        ('09:15:00', time(9, 15)),
        ('10:10', time(10, 10)),
        ('10:20:30.400', time(10, 20, 30, 400_000)),
        (b'10:20:30.400', time(10, 20, 30, 400_000)),
        (time(4, 8, 16), time(4, 8, 16)),
        (3610, time(1, 0, 10)),
        (3600.5, time(1, 0, 0, 500000)),
        (86400 - 1, time(23, 59, 59)),
        # Invalid inputs
        ('4:8:16', Err('Input should be in a valid time format, invalid character in hour [kind=time_parsing,')),
        (86400, Err('Input should be in a valid time format, numeric times may not exceed 86,399 seconds')),
        ('xxx', Err('Input should be in a valid time format, input is too short [kind=time_parsing,')),
        ('091500', Err('Input should be in a valid time format, invalid time separator, expected `:`')),
        (b'091500', Err('Input should be in a valid time format, invalid time separator, expected `:`')),
        ('09:15:90', Err('Input should be in a valid time format, second value is outside expected range of 0-59')),
        ('11:05:00Y', Err('Input should be in a valid time format, unexpected extra characters at the end of the inp')),
        # # https://github.com/pydantic/speedate/issues/10
        # ('11:05:00-05:30', time(11, 5, 0, tzinfo=create_tz(-330))),
        # ('11:05:00-0530', time(11, 5, 0, tzinfo=create_tz(-330))),
        # ('11:05:00Z', time(11, 5, 0, tzinfo=timezone.utc)),
        # ('11:05:00+00', time(11, 5, 0, tzinfo=timezone.utc)),
        # ('11:05-06', time(11, 5, 0, tzinfo=create_tz(-360))),
        # ('11:05+06', time(11, 5, 0, tzinfo=create_tz(360))),
        # ('11:05:00-25:00', errors.TimeError),
    ],
)
def test_time_parsing(TimeModel, value, result):
    if isinstance(result, Err):
        with pytest.raises(ValidationError, match=result.message_escaped()):
            TimeModel(d=value)
    else:
        assert TimeModel(d=value).d == result


@pytest.fixture(scope='module', name='DatetimeModel')
def datetime_model_fixture():
    class DatetimeModel(BaseModel):
        dt: datetime

    return DatetimeModel


@pytest.mark.parametrize(
    'value,result',
    [
        # Valid inputs
        # values in seconds
        (1_494_012_444.883_309, datetime(2017, 5, 5, 19, 27, 24, 883_309)),
        (1_494_012_444, datetime(2017, 5, 5, 19, 27, 24)),
        # values in ms
        (1_494_012_444_000, datetime(2017, 5, 5, 19, 27, 24)),
        ('2012-04-23T09:15:00', datetime(2012, 4, 23, 9, 15)),
        ('2012-04-23T09:15:00Z', datetime(2012, 4, 23, 9, 15, 0, 0, timezone.utc)),
        ('2012-04-23T10:20:30.400+02:30', datetime(2012, 4, 23, 10, 20, 30, 400_000, create_tz(150))),
        ('2012-04-23T10:20:30.400+02:00', datetime(2012, 4, 23, 10, 20, 30, 400_000, create_tz(120))),
        ('2012-04-23T10:20:30.400-02:00', datetime(2012, 4, 23, 10, 20, 30, 400_000, create_tz(-120))),
        (b'2012-04-23T10:20:30.400-02:00', datetime(2012, 4, 23, 10, 20, 30, 400_000, create_tz(-120))),
        (datetime(2017, 5, 5), datetime(2017, 5, 5)),
        (0, datetime(1970, 1, 1, 0, 0, 0)),
        # # Invalid inputs
        ('1494012444.883309', Err('Input should be a valid datetime, invalid date separator')),
        ('1494012444', Err('Input should be a valid datetime, invalid date separator')),
        (b'1494012444', Err('Input should be a valid datetime, invalid date separator')),
        ('1494012444000.883309', Err('Input should be a valid datetime, invalid date separator')),
        ('-1494012444000.883309', Err('Input should be a valid datetime, invalid character in year')),
        ('2012-4-9 4:8:16', Err('Input should be a valid datetime, invalid character in month')),
        ('x20120423091500', Err('Input should be a valid datetime, invalid character in year')),
        ('2012-04-56T09:15:90', Err('Input should be a valid datetime, day value is outside expected range')),
        ('2012-04-23T11:05:00-25:00', Err('Input should be a valid datetime, timezone offset must be less than 24 ho')),
        (19_999_999_999, datetime(2603, 10, 11, 11, 33, 19)),  # just before watershed
        (20_000_000_001, datetime(1970, 8, 20, 11, 33, 20, 1000)),  # just after watershed
        (1_549_316_052, datetime(2019, 2, 4, 21, 34, 12, 0)),  # nowish in s
        (1_549_316_052_104, datetime(2019, 2, 4, 21, 34, 12, 104_000)),  # nowish in ms
        (1_549_316_052_104_324, Err('Input should be a valid datetime, dates after 9999')),  # nowish in μs
        (1_549_316_052_104_324_096, Err('Input should be a valid datetime, dates after 9999')),  # nowish in ns
        ('infinity', Err('Input should be a valid datetime, input is too short')),
        (float('inf'), Err('Input should be a valid datetime, dates after 9999')),
        (float('-inf'), Err('Input should be a valid datetime, dates before 1600')),
        (1e50, Err('Input should be a valid datetime, dates after 9999')),
        (float('nan'), Err('Input should be a valid datetime, NaN values not permitted')),
    ],
)
def test_datetime_parsing(DatetimeModel, value, result):
    if isinstance(result, Err):
        with pytest.raises(ValidationError, match=result.message_escaped()):
            DatetimeModel(dt=value)
    else:
        assert DatetimeModel(dt=value).dt == result


@pytest.fixture(scope='module', name='TimedeltaModel')
def timedelta_model_fixture():
    class TimedeltaModel(BaseModel):
        d: timedelta

    return TimedeltaModel


@pytest.mark.parametrize(
    'delta',
    [
        timedelta(days=4, minutes=15, seconds=30, milliseconds=100),  # fractions of seconds
        timedelta(hours=10, minutes=15, seconds=30),  # hours, minutes, seconds
        timedelta(days=4, minutes=15, seconds=30),  # multiple days
        timedelta(days=1, minutes=00, seconds=00),  # single day
        timedelta(days=-4, minutes=15, seconds=30),  # negative durations
        timedelta(minutes=15, seconds=30),  # minute & seconds
        timedelta(seconds=30),  # seconds
    ],
)
def test_parse_python_format(TimedeltaModel, delta):
    assert TimedeltaModel(d=delta).d == delta
    # assert TimedeltaModel(d=str(delta)).d == delta


@pytest.mark.parametrize(
    'value,result',
    [
        # seconds
        (timedelta(seconds=30), timedelta(seconds=30)),
        (30, timedelta(seconds=30)),
        (30.1, timedelta(seconds=30, milliseconds=100)),
        (9.9e-05, timedelta(microseconds=99)),
        # minutes seconds
        ('00:15:30', timedelta(minutes=15, seconds=30)),
        ('00:05:30', timedelta(minutes=5, seconds=30)),
        # hours minutes seconds
        ('10:15:30', timedelta(hours=10, minutes=15, seconds=30)),
        ('01:15:30', timedelta(hours=1, minutes=15, seconds=30)),
        # ('100:200:300', timedelta(hours=100, minutes=200, seconds=300)),
        # days
        ('4d,00:15:30', timedelta(days=4, minutes=15, seconds=30)),
        ('4d,10:15:30', timedelta(days=4, hours=10, minutes=15, seconds=30)),
        # fractions of seconds
        ('00:15:30.1', timedelta(minutes=15, seconds=30, milliseconds=100)),
        ('00:15:30.01', timedelta(minutes=15, seconds=30, milliseconds=10)),
        ('00:15:30.001', timedelta(minutes=15, seconds=30, milliseconds=1)),
        ('00:15:30.0001', timedelta(minutes=15, seconds=30, microseconds=100)),
        ('00:15:30.00001', timedelta(minutes=15, seconds=30, microseconds=10)),
        ('00:15:30.000001', timedelta(minutes=15, seconds=30, microseconds=1)),
        (b'00:15:30.000001', timedelta(minutes=15, seconds=30, microseconds=1)),
        # negative
        ('-4d,00:15:30', timedelta(days=-4, minutes=-15, seconds=-30)),
        (-172800, timedelta(days=-2)),
        ('-00:15:30', timedelta(minutes=-15, seconds=-30)),
        ('-01:15:30', timedelta(hours=-1, minutes=-15, seconds=-30)),
        (-30.1, timedelta(seconds=-30, milliseconds=-100)),
        # iso_8601
        ('30', Err('Input should be a valid timedelta, "day" identifier')),
        ('P4Y', timedelta(days=1460)),
        ('P4M', timedelta(days=120)),
        ('P4W', timedelta(days=28)),
        ('P4D', timedelta(days=4)),
        ('P0.5D', timedelta(hours=12)),
        ('PT5H', timedelta(hours=5)),
        ('PT5M', timedelta(minutes=5)),
        ('PT5S', timedelta(seconds=5)),
        ('PT0.000005S', timedelta(microseconds=5)),
        (b'PT0.000005S', timedelta(microseconds=5)),
    ],
)
def test_parse_durations(TimedeltaModel, value, result):
    if isinstance(result, Err):
        with pytest.raises(ValidationError, match=result.message_escaped()):
            TimedeltaModel(d=value)
    else:
        assert TimedeltaModel(d=value).d == result


@pytest.mark.parametrize(
    'field, value, error_message',
    [
        ('dt', [], 'Input should be a valid datetime'),
        ('dt', {}, 'Input should be a valid datetime'),
        ('dt', object, 'Input should be a valid datetime'),
        ('d', [], 'Input should be a valid date'),
        ('d', {}, 'Input should be a valid date'),
        ('d', object, 'Input should be a valid date'),
        ('t', [], 'Input should be a valid time'),
        ('t', {}, 'Input should be a valid time'),
        ('t', object, 'Input should be a valid time'),
        ('td', [], 'Input should be a valid timedelta'),
        ('td', {}, 'Input should be a valid timedelta'),
        ('td', object, 'Input should be a valid timedelta'),
    ],
)
def test_model_type_errors(field, value, error_message):
    class Model(BaseModel):
        dt: datetime = None
        d: date = None
        t: time = None
        td: timedelta = None

    with pytest.raises(ValidationError) as exc_info:
        Model(**{field: value})
    assert len(exc_info.value.errors()) == 1
    error = exc_info.value.errors()[0]
    assert error['message'] == error_message


@pytest.mark.parametrize('field', ['dt', 'd', 't', 'dt'])
def test_unicode_decode_error(field):
    class Model(BaseModel):
        dt: datetime = None
        d: date = None
        t: time = None
        td: timedelta = None

    with pytest.raises(ValidationError) as exc_info:
        Model(**{field: b'\x81\x81\x81\x81\x81\x81\x81\x81'})
    assert exc_info.value.error_count() == 1
    # errors vary


def test_nan():
    class Model(BaseModel):
        dt: datetime
        d: date

    with pytest.raises(ValidationError) as exc_info:
        Model(dt=float('nan'), d=float('nan'))
    # insert_assert(exc_info.value.errors())
    assert exc_info.value.errors() == [
        {
            'kind': 'datetime_parsing',
            'loc': ['dt'],
            'message': 'Input should be a valid datetime, NaN values not permitted',
            'input_value': HasRepr('nan'),
            'context': {'error': 'NaN values not permitted'},
        },
        {
            'kind': 'date_from_datetime_parsing',
            'loc': ['d'],
            'message': 'Input should be a valid date or datetime, NaN values not permitted',
            'input_value': HasRepr('nan'),
            'context': {'error': 'NaN values not permitted'},
        },
    ]


@pytest.mark.parametrize(
    'constraint,msg,ok_value,error_value',
    [
        ('gt', 'greater than', date(2020, 1, 2), date(2019, 12, 31)),
        ('gt', 'greater than', date(2020, 1, 2), date(2020, 1, 1)),
        ('ge', 'greater than or equal to', date(2020, 1, 2), date(2019, 12, 31)),
        ('ge', 'greater than or equal to', date(2020, 1, 1), date(2019, 12, 31)),
        ('lt', 'less than', date(2019, 12, 31), date(2020, 1, 2)),
        ('lt', 'less than', date(2019, 12, 31), date(2020, 1, 1)),
        ('le', 'less than or equal to', date(2019, 12, 31), date(2020, 1, 2)),
        ('le', 'less than or equal to', date(2020, 1, 1), date(2020, 1, 2)),
    ],
)
def test_date_constraints(constraint, msg, ok_value, error_value):
    class Model(BaseModel):
        a: condate(**{constraint: date(2020, 1, 1)})

    assert Model(a=ok_value).dict() == {'a': ok_value}

    with pytest.raises(ValidationError, match=re.escape(f'Input should be {msg} 2020-01-01')):
        Model(a=error_value)


@pytest.mark.parametrize(
    'value,result',
    (
        ('1996-01-22', date(1996, 1, 22)),
        (date(1996, 1, 22), date(1996, 1, 22)),
    ),
)
def test_past_date_validation_success(value, result):
    class Model(BaseModel):
        foo: PastDate

    assert Model(foo=value).foo == result


@pytest.mark.parametrize(
    'value',
    (
        date.today(),
        date.today() + timedelta(1),
        '2064-06-01',
    ),
)
def test_past_date_validation_fails(value):
    class Model(BaseModel):
        foo: PastDate

    with pytest.raises(ValidationError) as exc_info:
        Model(foo=value)
    # insert_assert(exc_info.value.errors())
    assert exc_info.value.errors() == [
        {
            'kind': 'date_past',
            'loc': ['foo'],
            'message': 'Date should be in the past',
            'input_value': value,
        }
    ]


@pytest.mark.parametrize(
    'value,result',
    (
        (date.today() + timedelta(1), date.today() + timedelta(1)),
        ('2064-06-01', date(2064, 6, 1)),
    ),
)
def test_future_date_validation_success(value, result):
    class Model(BaseModel):
        foo: FutureDate

    assert Model(foo=value).foo == result


@pytest.mark.parametrize(
    'value',
    (
        date.today(),
        date.today() - timedelta(1),
        '1996-01-22',
    ),
)
def test_future_date_validation_fails(value):
    class Model(BaseModel):
        foo: FutureDate

    with pytest.raises(ValidationError) as exc_info:
        Model(foo=value)
    # insert_assert(exc_info.value.errors())
    assert exc_info.value.errors() == [
        {
            'kind': 'date_future',
            'loc': ['foo'],
            'message': 'Date should be in the future',
            'input_value': value,
        }
    ]
