from django.contrib import admin
from .models import Task, TaskComment, TaskStatusHistory


class TaskStatusHistoryInline(admin.TabularInline):
    model = TaskStatusHistory
    extra = 0
    readonly_fields = ["changed_by", "old_status", "new_status", "changed_at", "notes"]
    can_delete = False


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    readonly_fields = ["author", "content", "created_at"]
    can_delete = False


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        "id", "title", "priority", "status", "due_date",
        "assigned_to", "created_by", "created_at",
    ]
    list_filter = ["status", "priority", "due_date"]
    search_fields = ["title", "description"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at", "created_by"]
    raw_id_fields = ["assigned_to", "created_by"]
    inlines = [TaskStatusHistoryInline, TaskCommentInline]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TaskStatusHistory)
class TaskStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ["task", "old_status", "new_status", "changed_by", "changed_at"]
    list_filter = ["new_status", "changed_at"]
    readonly_fields = ["task", "old_status", "new_status", "changed_by", "changed_at", "notes"]
    ordering = ["-changed_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
