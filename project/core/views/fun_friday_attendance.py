from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime

from students.models import Student
from core.models import FunFridayAttendance
from core.views.students import get_next_friday, get_last_friday


@require_http_methods(["POST"])
def toggle_fun_friday_this_week(request, student_id):
    """Toggle a student's attendance for this week's Fun Friday."""
    student = get_object_or_404(Student, id=student_id)
    if student.is_adult:
        return JsonResponse({'success': False, 'error': 'Adult students cannot participate in Fun Friday'}, status=400)
    friday = get_next_friday()
    obj = FunFridayAttendance.objects.filter(student=student, date=friday).first()
    if obj:
        obj.delete()
        is_this_week = False
    else:
        FunFridayAttendance.objects.create(student=student, date=friday)
        is_this_week = True
    was_last_week = FunFridayAttendance.objects.filter(
        student=student, date=get_last_friday()
    ).exists()
    return JsonResponse({'success': True, 'is_this_week': is_this_week, 'was_last_week': was_last_week})


@require_http_methods(["POST"])
def add_fun_friday_attendance(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    try:
        data = json.loads(request.body)
        date_str = data.get('date')
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        obj, created = FunFridayAttendance.objects.get_or_create(student=student, date=parsed_date)
        return JsonResponse({'success': True, 'created': created, 'date': str(parsed_date)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def remove_fun_friday_attendance(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    try:
        data = json.loads(request.body)
        date_str = data.get('date')
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        deleted, _ = FunFridayAttendance.objects.filter(student=student, date=parsed_date).delete()
        return JsonResponse({'success': True, 'deleted': deleted > 0})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
