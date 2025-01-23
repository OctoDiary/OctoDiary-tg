#               © Copyright 2025
#          Licensed under the MIT License
#        https://opensource.org/licenses/MIT
#           https://github.com/OctoDiary

from datetime import datetime
import datetime as dt
from typing import Optional, List, Any

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
    origin: Any = None
    original_grade_from: Any = None
    original_grade_to: Any = None


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
    point_date: Any = None
    control_form_name: Optional[str] = None
    comment_exists: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    criteria: Any = None
    teacher: Optional[Teacher] = None
    date: Optional[str] = None
    activity: Optional[Activity] = None
    history: Optional[list] = None
    class_results: Optional[ClassResults] = None
    result_files: Any = None
    is_point: Optional[bool] = None
    is_exam: Optional[bool] = None
    original_grade_system_type: Optional[str] = None


class Url(Type):
    url: str
    type: str


class Material(Type):
    uuid: Optional[str] = None
    type: str
    selected_mode: Optional[str] = None
    type_name: str
    id: Optional[int] = None
    urls: List[Url]
    description: Any
    content_type: Any
    title: str
    action_id: int
    action_name: str


class Url1(Type):
    url: Optional[str] = None
    url_type: str


class Item(Type):
    id: Optional[int] = None
    uuid: Optional[str] = None
    title: str
    description: Optional[str] = None
    link: Optional[str] = None
    file_size: Optional[int] = None
    urls: List[Url1]
    average_rating: Any
    views: Any
    class_level_ids: Any
    created_at: Any
    updated_at: Any
    accepted_at: Any
    user_name: Any
    author: Any
    icon_url: Any
    full_cover_url: Any
    for_lesson: Any
    for_home: Any
    selected_mode: str
    partner_response: Any
    content_type: Any
    binding_id: Any
    is_necessary: bool
    is_hidden_from_students: bool


class AdditionalMaterial(Type):
    type: str
    type_name: str
    action_id: int
    action_name: str
    items: List[Item]


class HomeworkItem(Type):
    description: str
    comments: List
    materials: List[Material]
    homework: str
    homework_entry_student_id: int
    attachments: List
    subject_id: int
    date: dt.date
    date_assigned_on: str
    subject_name: str
    lesson_date_time: str
    additional_materials: List[AdditionalMaterial]
    is_done: bool
    has_teacher_answer: Optional[bool] = None
    homework_id: int
    homework_entry_id: int
    homework_created_at: str
    homework_updated_at: str
    written_answer: Any
    date_prepared_for: str


class Homeworks(Type):
    payload: List[HomeworkItem]
