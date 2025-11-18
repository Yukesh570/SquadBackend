# app/serializers.py
from rest_framework import serializers
from squadServices.models.navItem import NavItem, NavUserRelation

class NavItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NavItem
        fields = ['id', 'label', 'url', 'parent','order', 'is_active', 'icon']

class NavUserRelationSerializer(serializers.ModelSerializer):
    navigateId = NavItemSerializer(read_only=True)  

    class Meta:
        model = NavUserRelation
        fields = ['id', 'userType', 'navigateId', 'read', 'write', 'delete', 'put',]

class GetSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    permission = serializers.SerializerMethodField()
    userType=serializers.SerializerMethodField()
    class Meta:
        model = NavItem
        fields = ['id', 'label', 'url','userType', 'parent','order', 'is_active', 'icon','children','permission']
    def get_children(self, obj):
        children = NavItem.objects.filter(parent=obj)
        # Recursively serialize children    
        return GetSerializer(children, many=True, context=self.context).data
    
    def get_userType(self, obj):
        return self.context.get('userType')
    def get_permission(self, obj):
        userType = self.context.get('userType')
        try:
            relation = NavUserRelation.objects.get(navigateId=obj, userType=userType)
            return {
                "NavRelationid": relation.id,
                "read": relation.read,
                "write": relation.write,
                "delete": relation.delete,
                "put": relation.put,
            }
        except NavUserRelation.DoesNotExist:
            return None