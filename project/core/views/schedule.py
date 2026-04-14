import json

from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from core.models import FunFridayAttendance, HistoryLog, ScheduleSlot
from core.views.students import get_last_friday, get_next_friday
from students.models import Group, Student


def schedule_view(request):
    """Vista del horario semanal estilo Google Calendar."""
    groups = (
        Group.objects.filter(active=True)
        .select_related("teacher")
        .prefetch_related(
            models.Prefetch("students", queryset=Student.objects.filter(active=True).order_by("first_name"))
        )
        .order_by("group_name")
    )

    groups_list = list(groups)
    groups_data = []
    for g in groups_list:
        groups_data.append(
            {
                "id": g.id,
                "name": g.group_name,
                "color": g.color,
                "teacher": g.teacher.first_name,
                "students": [s.first_name for s in g.students.all()],
            }
        )

    saved = ScheduleSlot.objects.select_related("group").all()
    ROW_STARTS = ["16:10", "17:40", "19:10"]
    ROW_ENDS = ["17:30", "19:00", "20:30"]
    FRI_START = "16:00"
    FRI_END = "17:20"
    slots_data = []
    for s in saved:
        if s.day == 4:
            start, end = FRI_START, FRI_END
        else:
            start, end = ROW_STARTS[s.row], ROW_ENDS[s.row]
        slots_data.append(
            {"row": s.row, "day": s.day, "col": s.col, "group_id": s.group_id, "start": start, "end": end}
        )

    all_students_qs = Student.objects.filter(active=True).order_by("first_name", "last_name")
    students_data = [{"first_name": s.first_name, "last_name": s.last_name} for s in all_students_qs]

    return render(
        request,
        "schedule.html",
        {
            "groups_json": json.dumps(groups_data),
            "slots_json": json.dumps(slots_data),
            "students_json": json.dumps(students_data),
        },
    )


@require_http_methods(["POST"])
def save_schedule_slot(request):
    """Save a single schedule slot assignment to the database."""
    try:
        data = json.loads(request.body)
        row = int(data["row"])
        day = int(data["day"])
        col = int(data["col"])
        group_id = data.get("group_id")

        if group_id:
            group = get_object_or_404(Group, id=int(group_id))
            ScheduleSlot.objects.update_or_create(row=row, day=day, col=col, defaults={"group": group})
        else:
            ScheduleSlot.objects.filter(row=row, day=day, col=col).delete()

        HistoryLog.log_debounced(
            "schedule_updated",
            "Horario semanal actualizado",
            icon="calendar_month",
            minutes=5,
        )

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


def fun_friday_view(request):
    """Vista de Fun Friday con lista de estudiantes."""
    students = (
        Student.objects.filter(active=True, is_adult=False)
        .select_related("group")
        .order_by("group__group_name", "first_name")
    )
    this_friday = get_next_friday()
    last_friday = get_last_friday()

    # Single query for both weeks' attendance
    attendance = FunFridayAttendance.objects.filter(date__in=[this_friday, last_friday]).values_list(
        "student_id", "date"
    )
    this_week_ids = set()
    last_week_ids = set()
    for sid, att_date in attendance:
        if att_date == this_friday:
            this_week_ids.add(sid)
        else:
            last_week_ids.add(sid)

    # Filter from already-loaded students instead of re-querying
    students_list = list(students)
    this_week_students = [s for s in students_list if s.id in this_week_ids]
    last_week_students = [s for s in students_list if s.id in last_week_ids]

    return render(
        request,
        "fun_friday.html",
        {
            "students": students_list,
            "this_week_ids": this_week_ids,
            "last_week_ids": last_week_ids,
            "this_friday": this_friday,
            "last_friday": last_friday,
            "this_week_students": this_week_students,
            "last_week_students": last_week_students,
        },
    )
