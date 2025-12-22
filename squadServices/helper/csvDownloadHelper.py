import redis
from squad import settings
from squad.task import export_model_csv
from rest_framework.response import Response
import os
from rest_framework.permissions import AllowAny
from django.http import JsonResponse, FileResponse, Http404

from rest_framework.decorators import action
from rest_framework.decorators import action
from celery.result import AsyncResult
from django.http import HttpRequest

redis_client = redis.StrictRedis.from_url(settings.CELERY_RESULT_BACKEND)


def start_csv_export(
    self, request, module=None, model_name=None, fields=None, filter_dict=None
):

    # Convert queryset filters the same way DRF FilterSet does
    # filtered_qs = self.filter_queryset(self.get_queryset())
    # filter_dict = getattr(getattr(filtered_qs.query, 'where', None), 'children', [])
    filters = {}
    for f in filter_dict:
        try:
            filters[f.lhs.target.name] = f.rhs
        except:
            pass

    task = export_model_csv.delay(
        model_name=model_name, filters=filters, fields=fields or None, module=module
    )

    return Response({"task_id": task.id, "status": "processing"})


def csv_status(request: HttpRequest, module: str):

    task_id = request.GET.get("task_id")
    if not task_id:
        return Response({"error": "task_id required"}, status=400)
    progress = redis_client.get(task_id)
    if not progress:
        return JsonResponse({"ready": False, "progress": 0})
    progress = progress.decode()
    if progress.startswith("error:"):
        return JsonResponse({"ready": True, "error": progress[6:]})

    if progress == "100":
        filename = redis_client.get(f"{task_id}_result").decode()
        download_url = request.build_absolute_uri(
            f"/download-file/{module}/{filename}/"
        )
        return JsonResponse(
            {"ready": True, "progress": 100, "download_url": download_url}
        )

    return JsonResponse({"ready": False, "progress": int(progress)})


def download_file(request: HttpRequest, module: str, filename: str):

    file_path = os.path.join(settings.BASE_DIR, "media", "exports", filename)

    if not os.path.exists(file_path):
        raise Http404("File not found")
    file_handle = open(file_path, "rb")

    response = FileResponse(open(file_path, "rb"), as_attachment=True)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Content-Type"] = "text/csv"

    def remove_file_callback(response):
        try:
            file_handle.close()
            os.remove(file_path)
        except Exception as e:
            print("Error deleting file:", e)

    response.close = lambda *args, **kwargs: (
        FileResponse.close(response),
        remove_file_callback(response),
    )
    return response


def get_permissions(self):
    # Allow anyone for download_file
    if self.action == "download_file":
        return [AllowAny()]
    return super().get_permissions()
