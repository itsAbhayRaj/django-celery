from rest_framework import serializers

class EmailSerializer(serializers.Serializer):
    recipient = serializers.EmailField()
    subject = serializers.CharField(max_length=255)
    body = serializers.CharField()
    html_message = serializers.CharField(required=False, allow_null=True, allow_blank=True)

class BulkEmailSerializer(serializers.Serializer):
    recipients = serializers.ListField(
        child=serializers.EmailField()
    )
    subject = serializers.CharField(max_length=255)
    body = serializers.CharField()
    html_message = serializers.CharField(required=False, allow_null=True, allow_blank=True)