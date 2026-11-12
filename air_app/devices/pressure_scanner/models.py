from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ScanSettings:
    period: int = 250
    average: int = 10
    frames: int = 0
    units: str = 'PA'

    def __post_init__(self):
        if not 125 <= self.period <= 65535:
            raise ValueError('Period must be 125–65535 microseconds')
        if not 1 <= self.average <= 240:
            raise ValueError('Average must be 1–240')
        if not 0 <= self.frames <= 2147483648:
            raise ValueError('Frames must be 0–2147483648')
        if self.units not in ('PA', 'KPA', 'PSI', 'BAR'):
            raise ValueError('Unsupported pressure unit')

    @property
    def rate(self):
        return 1_000_000 / (self.period * 16 * self.average)

    def commands(self):
        # ASCII scrolling output, engineering units, timestamps, real sensors.
        return [('BIN', 0), ('FORMAT', 0), ('EU', 1), ('TIME', 1),
                ('SIM', 0), ('XSCANTRIG', 0), ('QPKTS', 1),
                ('UNITSCAN', self.units), ('PERIOD', self.period),
                ('AVG', self.average), ('FPS', self.frames)]

    def to_dict(self):
        return {**asdict(self), 'nominal_rate_hz': self.rate}


@dataclass
class Frame:
    number: int
    elapsed: float
    channels: dict
    device_time: float | None = None
    device_time_units: str | None = None
