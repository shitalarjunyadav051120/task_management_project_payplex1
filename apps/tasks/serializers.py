"""
Task Serializers - Validation and serialization for tasks, comments, history.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Task, TaskComment, TaskStatusHistory, TaskStatus
from apps.authentication.serializers import UserSerializer

User = get_user_model()


class TaskCommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = TaskComment
        fields = ["id", "task", "author", "content", "created_at", "updated_at"]
        read_only_fields = ["id", "task", "author", "created_at", "updated_at"]


class TaskCommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskComment
        fields = ["content"]

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Comment content cannot be empty.")
        return value.strip()


class TaskStatusHistorySerializer(serializers.ModelSerializer):
    changed_by = UserSerializer(read_only=True)

    class Meta:
        model = TaskStatusHistory
        fields = ["id", "old_status", "new_status", "changed_by", "changed_at", "notes"]
        read_only_fields = fields


class TaskSerializer(serializers.ModelSerializer):
    assigned_to = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    comments = TaskCommentSerializer(many=True, read_only=True)
    status_history = TaskStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id", "title", "description", "priority", "status",
            "due_date", "assigned_to", "created_by",
            "comments", "status_history",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class TaskListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — no nested comments/history."""
    assigned_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id", "title", "priority", "status", "due_date",
            "assigned_to_name", "created_by_name", "created_at",
        ]

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.get_full_name() if obj.assigned_to else None

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class TaskCreateSerializer(serializers.ModelSerializer):
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        source="assigned_to",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Task
        fields = [
            "title", "description", "priority", "status",
            "due_date", "assigned_to_id",
        ]

    def validate_due_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Due date cannot be in the past.")
        return value


class TaskUpdateSerializer(serializers.ModelSerializer):
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        source="assigned_to",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Task
        fields = [
            "title", "description", "priority", "status",
            "due_date", "assigned_to_id",
        ]

    def validate_due_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Due date cannot be in the past.")
        return value


class TaskStatusUpdateSerializer(serializers.Serializer):
    """Used specifically for status-change endpoint with optional notes."""
    status = serializers.ChoiceField(choices=TaskStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
