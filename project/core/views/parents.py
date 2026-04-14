from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from students.forms import ParentForm
from students.models import Parent


class ParentCreateView(CreateView):
    model = Parent
    form_class = ParentForm
    template_name = "parent_create.html"

    def get_success_url(self):
        return reverse_lazy("student_create") + f"?parent_id={self.object.id}"

    def form_valid(self, form):
        try:
            dni = form.cleaned_data.get("dni")
            existing_parent = Parent.objects.filter(dni=dni).first()

            if existing_parent:
                messages.info(
                    self.request,
                    f"El padre/tutor {existing_parent.full_name} ya existe. Serás redirigido para crear un estudiante.",
                )
                self.object = existing_parent
                return HttpResponseRedirect(self.get_success_url())

            self.object = form.save()
            messages.success(
                self.request,
                f"Padre/tutor {self.object.full_name} creado exitosamente. Ahora crea un estudiante para este padre.",
            )
            return HttpResponseRedirect(self.get_success_url())

        except Exception as e:
            messages.error(self.request, f"Error al crear el padre: {str(e)}")
            return self.form_invalid(form)
