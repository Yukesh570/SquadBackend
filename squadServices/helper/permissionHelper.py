from squadServices.models.email import EmailHost
from squadServices.models.navItem import NavUserRelation
from rest_framework.exceptions import PermissionDenied


# external helper
def check_permission(view, permission_type, module=None):
    if module is None:
        module = view.kwargs.get('module')
        if module is not None:
            module = module.lower()

    user = view.request.user
    if permission_type not in ['read', 'write', 'put', 'delete']:
        raise ValueError(f"Invalid permission type: {permission_type}")

    permissions_qs = NavUserRelation.objects.filter(
        userType=user.userType,
        navigateId__url__icontains=module
    ).values_list(permission_type, flat=True)
    if not any(permissions_qs):
        
        raise PermissionDenied(f"You do not have {permission_type} permission to perform this action.")
