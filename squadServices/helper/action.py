from squadServices.models.notificationModel.notification import Notification
from squadServices.models.users import UserLog


def log_action_delete(user, title, name):
    Notification.objects.create(
        title=title,
        description=f"{title} named '{name}' has been deleted.",
        createdBy=user,
        updatedBy=user,
    )
    UserLog.objects.create(
        user=user,
        title=title,
        action=f"{title} '{name}' deleted.",
        createdBy=user,
        updatedBy=user,
    )


def log_action_update(user, title, name):
    Notification.objects.create(
        title=title,
        description=f"{title} named '{name}' has been updated .",
        createdBy=user,
        updatedBy=user,
    )
    UserLog.objects.create(
        user=user,
        title=title,
        action=f"{title} '{name}' updated.",
        createdBy=user,
        updatedBy=user,
    )


def log_action_create(user, title, name):
    Notification.objects.create(
        title=title,
        description=f"New {title} named '{name}' has been created.",
        createdBy=user,
        updatedBy=user,
    )
    UserLog.objects.create(
        user=user,
        title=title,
        action=f"{title} '{name}' created.",
        createdBy=user,
        updatedBy=user,
    )


def log_action_export(user, title):
    Notification.objects.create(
        title=title,
        description=f"{title} CSV export has been initiated.",
        createdBy=user,
        updatedBy=user,
    )
    UserLog.objects.create(
        user=user,
        title=title,
        action=f"{title} CSV export initiated.",
        createdBy=user,
        updatedBy=user,
    )


def log_action_import(user, title):
    Notification.objects.create(
        title=title,
        description=f"{title}  CSV import has started.",
        createdBy=user,
        updatedBy=user,
    )
    UserLog.objects.create(
        user=user,
        title=title,
        action=f"{title} CSV import started.",
        createdBy=user,
        updatedBy=user,
    )
