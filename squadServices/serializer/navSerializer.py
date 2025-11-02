# app/serializers.py
from rest_framework import serializers
from squadServices.models.navItem import NavItem, NavUserRelation

class NavItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NavItem
        fields = ['id', 'label', 'url', 'order', 'is_active', 'icon']


class NavUserRelationSerializer(serializers.ModelSerializer):
    navigateId = NavItemSerializer(read_only=True)  

    class Meta:
        model = NavUserRelation
        fields = ['id', 'userType', 'navigateId', 'read', 'write', 'delete', 'put']