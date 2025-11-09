from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets, status
from squad.utils.authenticators import JWTAuthentication
from squadServices.models.navItem import NavItem, NavUserRelation
from squadServices.models.users import UserType
from squadServices.serializer.navSerializer import (
    GetSerializer,
    NavItemSerializer,
    NavUserRelationSerializer,
)
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action


class NavItemViewSet(viewsets.ModelViewSet):
    queryset = NavItem.objects.all()
    serializer_class = NavItemSerializer
    # 👇 Require JWT token authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.action == "list":

            return NavItem.objects.filter(is_active=True)
        return super().get_queryset()
        
        
class GetNavUserRelationViewSet(viewsets.ModelViewSet):
    serializer_class = GetSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return NavItem.objects.filter(parent=None, is_active=True)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['userType'] = self.request.user.userType
        return context
    def getByUserType(self, request, *args, **kwargs):
        userType = kwargs.get("userType")
        related_nav_ids = NavUserRelation.objects.filter(userType=userType).values_list('navigateId', flat=True)
        nav_items = NavItem.objects.filter(id__in=related_nav_ids, parent=None, is_active=True)
        
        serializer = self.get_serializer(nav_items, many=True, context={'userType': userType})
        return Response(serializer.data)

class NavUserRelationViewSet(viewsets.ModelViewSet):
    queryset = NavUserRelation.objects.all()
    serializer_class = NavUserRelationSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
            user = self.request.user
            if self.action == "list":
                return NavUserRelation.objects.filter(userType=user.userType,navigateId__parent=None)
            return super().get_queryset()
    def create(self, request, *args, **kwargs):
        userType = request.data.get("userType")
        if not userType:
            return Response(
                {"error": "userType is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        navItems = NavItem.objects.filter(is_active=True)
        if NavUserRelation.objects.filter(userType=userType).exists():
            return Response(
                {"error": "userType already exists"}, status=status.HTTP_400_BAD_REQUEST
            )
        relations = [
            NavUserRelation(
                userType=userType,
                navigateId=navItem,
                read=False,
                write=False,
                delete=False,
                put=False,
            )
            for navItem in navItems
        ]
        NavUserRelation.objects.bulk_create(relations)
        return Response(
            {"message": f"{len(relations)} NavUserRelation created for '{userType}'."},
            status=status.HTTP_201_CREATED,
        )
    def createSidebar(self, request, *args, **kwargs):
        label = request.data.get("label")
        if not label:
                return Response(
                    {"error": "label is required"}, status=status.HTTP_400_BAD_REQUEST
                )
        navItems = NavItem.objects.filter(label=label).first()
        print("navItems", navItems.id)
        if NavUserRelation.objects.filter(navigateId=navItems.id).exists():
            return Response(
                {"error": "label already exists"}, status=status.HTTP_400_BAD_REQUEST
            )
        relations = [
            NavUserRelation(
                userType=value,
                navigateId=navItems,
                read=True,
                write=False,
                delete=False,
                put=False,
            )
            for value, label in UserType.choices
        ]
        NavUserRelation.objects.bulk_create(relations)
        return Response(
            {"message": f"{len(relations)} NavUserRelation created for '{label}'."},
            status=status.HTTP_201_CREATED,
        )

    
    def getByUserType(self, request, *args, **kwargs):
        print("kwarg============s",kwargs)
        userType = kwargs.get("userType")
        relations = NavUserRelation.objects.filter(userType=userType)
        serializer = self.get_serializer(relations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=["patch"], url_path="bulk-update")
    def bulk_partial_update(self, request, *args, **kwargs):
        data = request.data
        if not isinstance(data, list):
            return Response({"error": "Expected a list of objects."}, status=status.HTTP_400_BAD_REQUEST)

        updated_items = []
        for item in data:
            obj_id = item.get("id")
            if not obj_id:
                continue 

            try:
                instance = NavUserRelation.objects.get(id=obj_id)
            except NavUserRelation.DoesNotExist:
                continue

            serializer = self.get_serializer(instance, data=item, partial=True)
            if serializer.is_valid():
                serializer.save()
                updated_items.append(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({"updated": updated_items}, status=status.HTTP_200_OK)
