from datetime import datetime
from typing import Optional

from octodiary.types.model import Type


class Grade(Type):
    origin: Optional[str] = None
    five: Optional[float] = None
    hundred: Optional[float] = None


class Value(Type):
    name: Optional[str] = None
    nmax: Optional[float] = None
    grade: Optional[Grade] = None
    grade_system_id: Optional[int] = None
    grade_system_type: Optional[str] = None


class Teacher(Type):
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    birth_date: Optional[str] = None
    sex: Optional[str] = None
    user_id: Optional[int] = None


class Activity(Type):
    schedule_item_id: Optional[int] = None
    lesson_topic: Optional[str] = None


class MarkValue(Type):
    five: Optional[int] = None
    origin: None = None
    original_grade_from: None = None
    original_grade_to: None = None


class MarksDistribution(Type):
    percentage_of_students: Optional[int] = None
    number_of_students: Optional[int] = None
    mark_value: Optional[MarkValue] = None


class ClassResults(Type):
    total_students: Optional[int] = None
    marks_distributions: Optional[list[MarksDistribution]] = None


class MarkInfo(Type):
    id: Optional[int] = None
    value: Optional[str] = None
    values: Optional[list[Value]] = None
    comment: Optional[str] = None
    weight: Optional[int] = None
    point_date: None = None
    control_form_name: Optional[str] = None
    comment_exists: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    criteria: None = None
    teacher: Optional[Teacher] = None
    date: Optional[str] = None
    activity: Optional[Activity] = None
    history: Optional[list] = None
    class_results: Optional[ClassResults] = None
    result_files: None = None
    is_point: Optional[bool] = None
    is_exam: Optional[bool] = None
    original_grade_system_type: Optional[str] = None
