from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsHunter(BasePermission):
    message = "Seul un chasseur de primes peut effectuer cette action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "hunter_profile")
        )


class IsSheriff(BasePermission):
    message = "Seul un shérif peut effectuer cette action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "sheriff_profile")
        )


class CanManageWantedPerson(BasePermission):
    message = "Seul un shérif peut gérer les personnes recherchées."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        return IsSheriff().has_permission(request, view)


class CanManageBountyMission(BasePermission):
    message = "Vous n'avez pas la permission d'effectuer cette action."

    def has_permission(self, request, view):
        if view.action == "claim":
            return IsHunter().has_permission(request, view)

        if view.action in ["validate_result", "reject_result"]:
            return IsSheriff().has_permission(request, view)

        if request.method in SAFE_METHODS:
            return True

        return IsSheriff().has_permission(request, view)


class CanViewHunter(BasePermission):
    message = "Vous devez être chasseur pour accéder à votre profil."

    def has_permission(self, request, view):
        if view.action == "me":
            return IsHunter().has_permission(request, view)

        return request.method in SAFE_METHODS
