from enum import Enum
from typing import List, Optional, Union
from datetime import date, datetime
from pydantic import BaseModel, Field

reasoning: str = Field(
    description="Precise and strict explanation of the strategy described by user, explicitly mentioning entities, metrics, evaluations and actions."
)

# region Enums


# Наследуемся от str, чтобы при сериализации в JSON получались строки ("HOURLY"),
# а не объекты enum.


class PeriodOptionEnum(str, Enum):
    LAST_HOUR = "last hour"
    TODAY = "today"
    YESTERDAY = "yesterday"
    TWO_DAYS_AGO = "two days ago"
    THREE_DAYS_AGO = "three days ago"
    LAST_WEEK = "last week"
    LAST_TWO_WEEKS = "last two weeks"
    LAST_MONTH = "last month"


class FrequencyEnum(str, Enum):
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class WeekDayEnum(str, Enum):
    MO = "MO"
    TU = "TU"
    WE = "WE"
    TH = "TH"
    FR = "FR"
    SA = "SA"
    SU = "SU"


class CampaignTypeEnum(str, Enum):
    UNIFIED = "unified"
    ALL = "all"
    MANUAL = "manual"


class CalculationFunctionEnum(str, Enum):
    AVG = "avg"
    MIN = "min"
    MAX = "max"


class CalculationRangeEnum(str, Enum):
    CAMPAIGN = "campaign"
    PRODUCT = "product"


class OperatorEnum(str, Enum):
    LESS_THAN = "<"
    GREATER_THAN = ">"
    EQUALS = "="
    GREATER_THAN_OR_EQUAL = ">="
    LESS_THAN_OR_EQUAL = "<="
    NOT_EQUALS = "!="


class LogicLinkEnum(str, Enum):
    AND = "AND"
    OR = "OR"


# endregion

# region Атомарные элементы
class OneTimeSchedule(BaseModel):
    datetime_at: datetime = Field(
        ...,
        description="The specific date when the event must be executed. Format: 'YYYY-MM-DD-HH-mm'.",
    )


class RecurringSchedule(BaseModel):
    frequency: FrequencyEnum = Field(
        ...,
        description="The base frequency of the schedule. Describes how often the branch must be executed",
    )
    interval: int = Field(
        1,
        ge=1,
        description="The interval of recurrence with given frequency (e.g., FREQ = DAILY, INTERVAL = 2 means 'every 2 days').",
    )
    by_day: Optional[List[WeekDayEnum]] = Field(
        ..., description="List of days if frequency is WEEKLY (e.g., ['MO', 'WE'])."
    )
    by_hour: Optional[List[int]] = Field(
        ...,
        ge=0,
        le=23,
        description=(
            "List of hours in 24-hour format (0-23) when the event should occur "
            "if frequency is DAILY or WEEKLY (e.g., [9, 17] for 9:00 and 17:00). "
            "Valid values are 0 to 23, as in iCalendar RRULE BYHOUR."
        ),
    )
    start_date: Optional[date] = Field(
        ...,
        description="The specific date to start the schedule (inclusive). If null, the schedule starts immediately upon creation. Format: 'YYYY-MM-DD'.",
    )
    end_date: Optional[date] = Field(
        ...,
        description="The specific date to stop the schedule (inclusive). If null, the schedule runs indefinitely. Format: 'YYYY-MM-DD'.",
    )
    # by_minute не делаем, чтобы не повышать нагрузку на сервак, а то все поставят в 0 и 30 минут, будут пики


class StaticPeriod(BaseModel):
    date_from: date = Field(
        ...,
        alias="from",
        description="Start date of a period. Must be a static date 'YYYY-MM-DD'",
    )

    date_to: date = Field(
        ...,
        alias="to",
        description="End date of a period. Must be a static date 'YYYY-MM-DD'",
    )


class Calculation(BaseModel):
    calculation_function: CalculationFunctionEnum = Field(
        ...,
        description="Mathematical function required to calculate aggregated metric upon user's request",
    )

    calculation_range: CalculationRangeEnum = Field(
        ...,
        description="Data range for aggregated metric defined by user. Example: 'ниже среднего по кампании' - campaign, 'ниже среднего значения среди кластеров по товару' - product. If campaign only has one product, use campaign.",
    )


# endregion

# region Составные элементы внутри ветвей

class ConditionDetail(BaseModel):
    variable_id: str = Field(
        ..., description="ID of the variable from a dictionary of available variables"
    )

    operator: OperatorEnum = Field(..., description="Comparison operator")

    value: Union[int, float, str, Calculation] = Field(..., description="Comparison value")

    period: Optional[Union[StaticPeriod, PeriodOptionEnum]] = Field(
        ...,
        description="Optional date range for the condition. Prescribes to aggregate metric's value through that date range. "
        "Either a static period with defined start and end or dynamci period described by one of the keywords of PeriodOptionEnum.",
    )


class ConditionWrapper(BaseModel):
    logic_link: Optional[LogicLinkEnum] = Field(
        ..., description="Logical operator between two conditions if needed (or null)"
    )
    condition: ConditionDetail


class ActionItem(BaseModel):
    action: str = Field(
        ..., description="Action ID chosen from a dictionary of available actions"
    )  # Подставить словарь действий для выбора // Переменные и сущности в действие подставляет компилятор
    action_value: Optional[Union[int, float, str]] = Field(
        ...,
        description="Action value. Must match the required value type. If required value type is null, action_value must be null. ",
    )  # Здесь в компиляторе добавить проверку типов и приведение типов


# endregion

# region Верхнеуровневые элементы стратегии
class CampaignProductLink(BaseModel):
    campaign_id: str = Field(
        ..., 
        description="Идентификатор рекламной кампании (числовая строка)."
    )
    product_ids: List[str] = Field(
        ..., 
        description="Список идентификаторов товаров (номенклатур), относящихся к данной РК в рамках стратегии."
    )

class StaticSets(BaseModel):
    links: Optional[List[CampaignProductLink]] = Field(
        default=None,
        description="Список связок Кампания-Товары для статического управления."
    )

class Branch(BaseModel):
    conditions: Optional[List[ConditionWrapper]] = Field(
        ...,
        description="List of conditions for this branch. Conditions determine execution of this branch' action. If no specific conditions stated by user, leave empty",
        max_length=3,
    )
    action: ActionItem
    schedule: Union[OneTimeSchedule, RecurringSchedule] = Field(
        ...,
        description="Defines whether the strategy runs once or follows a recurring pattern.",
    )

class StrategyResponse(BaseModel):
    static_sets: StaticSets
    branches: List[Branch]

# endregion
