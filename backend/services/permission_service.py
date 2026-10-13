"""Role-based access rules for project workspaces and folder mutations.

PRISM separates project workspaces by BIMA project-number prefix:

* ``13`` - Engineering projects (inspection, review, technical documents).
* ``03`` - Internal HR/GA/Finance projects (administration).

Folder and workspace mutations are restricted to the roles that own the
matching domain. Superusers can always act. The rules live here so the API and
future callers share one decision point.
"""

from __future__ import annotations

from domain.enums import UserRole

ENGINEERING_PREFIX = "13"
INTERNAL_PREFIX = "03"

#: Roles with unrestricted workspace oversight (project listing, document
#: review, assignment). HRGA and FINANCE deliberately stay out: they only
#: manage internal projects and must not inherit lead-level document access.
PRIVILEGED_ROLES = frozenset({UserRole.LEAD_ENGINEER, UserRole.SUPERUSER})

ENGINEERING_ROLES = frozenset({UserRole.ENGINEER, UserRole.LEAD_ENGINEER, UserRole.SUPERUSER})
INTERNAL_ROLES = frozenset({UserRole.HRGA, UserRole.FINANCE, UserRole.SUPERUSER})


class ProjectKind:
    """Classification of a project by its number prefix."""

    ENGINEERING = "ENGINEERING"
    INTERNAL = "INTERNAL"
    UNCLASSIFIED = "UNCLASSIFIED"


def project_kind(project_number: str | None) -> str:
    """Classify a project number into engineering, internal, or unclassified.

    A project without a number is unclassified: the classification cannot be
    derived, so the legacy behaviour applies and no extra restriction is added.
    """

    number = (project_number or "").strip()
    if number.startswith(ENGINEERING_PREFIX):
        return ProjectKind.ENGINEERING
    if number.startswith(INTERNAL_PREFIX):
        return ProjectKind.INTERNAL
    return ProjectKind.UNCLASSIFIED


def roles_for_kind(kind: str) -> frozenset[UserRole] | None:
    """Return the roles allowed to mutate folders for a project kind.

    ``None`` means the kind is unclassified and unrestricted.
    """

    if kind == ProjectKind.ENGINEERING:
        return ENGINEERING_ROLES
    if kind == ProjectKind.INTERNAL:
        return INTERNAL_ROLES
    return None


def is_privileged(role: UserRole | str | None) -> bool:
    """Return whether the role has lead-level workspace oversight."""

    resolved = _resolved(role)
    return resolved in PRIVILEGED_ROLES if resolved is not None else False


def has_workspace_oversight(user: object | None) -> bool:
    """Return whether ``user`` may read every workspace regardless of ownership.

    Oversight comes from the role (lead engineers) or from the local
    ``is_superuser`` flag, which is the only way to grant cross-department
    access because BIMA's flat directory cannot express it.
    """

    if user is None:
        return False
    if bool(getattr(user, "is_superuser", False)):
        return True
    return is_privileged(getattr(user, "role", None))


def can_review_document(user: object | None, document: object | None) -> bool:
    """Return whether ``user`` may submit or finalize ``document``'s review.

    Allowed for the local superuser, the document uploader, the project owner,
    and the engineer the document is currently assigned to. The legacy rule
    required the assigned PIC *only*, which locked out the uploader and the
    project owner; assignment stays valid but is no longer the sole key.
    """

    if user is None or document is None:
        return False
    if bool(getattr(user, "is_superuser", False)):
        return True
    user_id = getattr(user, "id", None)
    if user_id is None:
        return False
    if user_id == getattr(document, "owner_id", None):
        return True
    if user_id == getattr(document, "assigned_to_id", None):
        return True
    project = getattr(document, "project", None)
    return project is not None and user_id == getattr(project, "owner_id", None)


def can_manage_folders(role: UserRole | str | None, project_number: str | None) -> bool:
    """Return whether ``role`` may add or edit folders on the project."""

    allowed = roles_for_kind(project_kind(project_number))
    if allowed is None:
        return True
    resolved = _resolved(role)
    return resolved in allowed if resolved is not None else False


def can_create_project(role: UserRole | str | None, project_number: str | None) -> bool:
    """Return whether ``role`` may create a project with this number.

    Creating a project creates its workspace folder, so numbered projects
    follow the folder rules (13 engineering, 03 internal). Unnumbered projects
    keep the legacy lead-only behaviour because the kind cannot be derived.
    """

    if project_kind(project_number) == ProjectKind.UNCLASSIFIED:
        return is_privileged(role)
    return can_manage_folders(role, project_number)


def folder_permission_message(project_number: str | None) -> str:
    """Explain the folder rule for a rejected request."""

    kind = project_kind(project_number)
    if kind == ProjectKind.ENGINEERING:
        return (
            "Only engineers, lead engineers, or superusers can manage folders on "
            "engineering projects (number prefix 13)."
        )
    if kind == ProjectKind.INTERNAL:
        return (
            "Only HR/GA, finance, or superusers can manage folders on internal "
            "projects (number prefix 03)."
        )
    return "You do not have permission to manage folders on this project."


def create_permission_message(project_number: str | None) -> str:
    """Explain the create-project rule for a rejected request."""

    kind = project_kind(project_number)
    if kind == ProjectKind.ENGINEERING:
        return (
            "Only engineers, lead engineers, or superusers can create engineering "
            "projects (number prefix 13)."
        )
    if kind == ProjectKind.INTERNAL:
        return (
            "Only HR/GA, finance, or superusers can create internal projects "
            "(number prefix 03)."
        )
    return "Only lead engineers or superusers can create projects without a project number."


def _resolved(role: UserRole | str | None) -> UserRole | None:
    if role is None:
        return None
    try:
        return UserRole(str(role))
    except ValueError:
        return None
