from rest_framework import serializers
from .models import ContractTemplate

class ContractTemplateSerializer(serializers.ModelSerializer):
    # Only read-only fields for creation/update timestamps and creator
    created_by_username = serializers.ReadOnlyField(source='created_by.username')

    class Meta:
        model = ContractTemplate
        fields = [
            'id', 
            'name', 
            'content', 
            'template_file', 
            'is_public', 
            'created_at', 
            'updated_at',
            'created_by_username'
        ]
        read_only_fields = ('created_at', 'updated_at', 'created_by_username')