# students — People Management

The `students` app owns all people-related models: students, parents, teachers, and groups. It is the foundation that billing and comms depend on.

## Models

| Model | Table | Key Fields | Relationships |
| ----- | ----- | ---------- | ------------- |
| **Teacher** | `teachers` | first_name, last_name, email (unique), phone, active, admin | Has many Groups |
| **Group** | `groups` | group_name (unique), color (hex), active | FK to Teacher; has many Students |
| **Parent** | `parents` | first_name, last_name, dni (unique), phone, email, iban | M2M to Students via StudentParent |
| **Student** | `students` | first_name, last_name, birth_date, is_adult, school, allergies, gdpr_signed, active | FK to Group; M2M to Parents |
| **StudentParent** | `student_parents` | student, parent | Through table for Student-Parent M2M |

### Key Properties

- `Student.full_name` — "{first_name} {last_name}"
- `Student.age` — calculated from birth_date
- `Parent.full_name` — "{first_name} {last_name}"
- `Teacher.full_name` — "{first_name} {last_name}"

## Forms

- **StudentForm** — ModelForm for Student (first_name, last_name, birth_date, school, allergies, gdpr_signed, group). Validates birth_date is not in the future.
- **ParentForm** — ModelForm for Parent (first_name, last_name, dni, phone, email, iban). Validates DNI minimum 8 characters.
- **ParentFormSet** — Inline formset for StudentParent through model.

## Admin

- `StudentAdmin` with `StudentParentInline` — fieldsets for personal, school, health, status info
- `ParentAdmin` with `ParentStudentInline` — fieldsets for personal and contact info
- `StudentParentAdmin` with autocomplete
- `Teacher` and `Group` — simple registration

## URL Patterns (students/urls.py)

| URL | View | Name |
| --- | ---- | ---- |
| `parents/create/` | ParentCreateView | `parent_create` |
| `students/` | StudentListView | `students_list` |
| `students/create/` | StudentCreateView | `student_create` |
| `students/<id>/` | StudentDetailView | `student_detail` |
| `students/<id>/update/` | StudentUpdateView | `student_update` |
| `api/students/<id>/fun-friday/toggle/` | toggle_fun_friday_this_week | `toggle_fun_friday_this_week` |
| `api/students/<id>/fun-friday/add/` | add_fun_friday_attendance | `add_fun_friday_attendance` |
| `api/students/<id>/fun-friday/remove/` | remove_fun_friday_attendance | `remove_fun_friday_attendance` |
| `api/search/students/` | search_students | `search_students` |
| `api/search/parents/` | search_parents | `search_parents` |
| `api/validate/student-parent/` | validate_student_parent | `validate_student_parent` |

## Cross-App Communication

- **Depended on by**: billing (FK from Enrollment/Payment to Student/Parent), comms (email recipients), core (schedule slots, fun friday)
- **Depends on**: nothing — students is the foundational app
- **Note**: Views currently live in `core/views/students.py` and `core/views/parents.py`. URL routing happens here, view code is imported from core.
