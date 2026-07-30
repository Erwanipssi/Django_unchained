from django.shortcuts import render
from django.views.generic import DetailView, ListView, TemplateView

from .models import BountyMission, WantedPerson


def home(request):
    return render(
        request,
        "bounties/home.html",
        {
            "wanted_count": WantedPerson.objects.filter(
                status=WantedPerson.Status.WANTED
            ).count(),
            "mission_count": BountyMission.objects.filter(
                status=BountyMission.Status.OPEN
            ).count(),
        },
    )


class WantedPersonListView(ListView):
    model = WantedPerson
    template_name = "bounties/wanted_list.html"
    context_object_name = "wanted_persons"
    ordering = ["name"]


class WantedPersonDetailView(DetailView):
    model = WantedPerson
    template_name = "bounties/wanted_detail.html"
    context_object_name = "person"


class MissionListView(ListView):
    model = BountyMission
    template_name = "bounties/mission_list.html"
    context_object_name = "missions"
    ordering = ["-id"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("wanted_person", "hunter")
        )


class LoginView(TemplateView):
    template_name = "bounties/login.html"


class WantedCreateView(TemplateView):
    template_name = "bounties/wanted_create.html"


class MissionCreateView(TemplateView):
    template_name = "bounties/mission_create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["wanted_persons"] = WantedPerson.objects.filter(
            status=WantedPerson.Status.WANTED
        ).order_by("name")
        return context
