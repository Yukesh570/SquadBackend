# squadServices/views/vendor_rate_import_view.py

import uuid
import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
import redis
import csv

from squadServices.models.mappingSetup.mappingSetup import MappingSetup

redis_client = redis.StrictRedis.from_url(os.getenv("CELERY_RESULT_BACKEND"))

from squad.task import import_vendor_rate_task


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_vendor_rate_csv(request):
    """
    Upload CSV and start Celery import task.
    """
    file = request.FILES.get("file")
    mapped_id = request.data.get("mapped")
    mapping = MappingSetup.objects.filter(id=mapped_id).first()
    print("!!!!!!!!!!!!!!!!!!!!!!!", mapping)
    print(settings.CELERY_BROKER_URL)
    print(settings.CELERY_RESULT_BACKEND)

    if not file:
        return Response({"error": "CSV file is required"}, status=400)
    if not mapping:
        return Response({"error": "Mapping setup not found"}, status=400)
    header_map = {
        mapping.ratePlan.lower().strip(): "ratePlan",
        mapping.country.lower().strip(): "country",
        mapping.countryCode.lower().strip(): "countryCode",
        mapping.timeZone.lower().strip(): "timeZone",
        mapping.network.lower().strip(): "network",
        mapping.MCC.lower().strip(): "MCC",
        mapping.MNC.lower().strip(): "MNC",
        mapping.rate.lower().strip(): "rate",
        mapping.dateTime.lower().strip(): "dateTime",
    }
    try:
        # Read header only
        file_data = file.read().decode("utf-8").splitlines()
        reader = csv.reader(file_data)
        csv_headers = next(reader)

        for col in csv_headers:
            normalized_col = col.lower().strip()
            if normalized_col not in header_map:
                return Response(
                    {
                        "status": "error",
                        "error": f"Header '{col}' does not match mapping setup.",
                        "required_headers": list(header_map.keys()),
                    },
                    status=400,
                )

    except Exception as e:
        return Response({"error": "Invalid CSV file", "details": str(e)}, status=400)

    # reset file pointer so it can be saved later
    file.seek(0)
    # Save file temporarily
    filename = f"vendorRate_{uuid.uuid4().hex}.csv"
    temp_path = os.path.join(settings.MEDIA_ROOT, "imports")
    os.makedirs(temp_path, exist_ok=True)
    filepath = os.path.join(temp_path, filename)
    print("Saving CSV to:", filepath)

    with open(filepath, "wb") as out:
        for chunk in file.chunks():
            out.write(chunk)

    # Create task ID manually so we can track it
    task_id = uuid.uuid4().hex

    # Trigger Celery task
    import_vendor_rate_task.apply_async(
        args=[filepath, request.user.id, task_id, mapping.id], task_id=task_id
    )

    return Response({"message": "Import started", "task_id": task_id})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_rate_import_status(request, task_id):
    """
    Check progress of import.
    """
    progress = redis_client.get(task_id)
    if not progress:
        return Response({"status": "not-found"}, status=404)

    progress = progress.decode()

    # If error occurred
    if progress.startswith("error:"):
        return Response({"status": "error", "message": progress[6:]})

    # If finished
    if progress == "100":
        final = redis_client.get(f"{task_id}_result")
        final = final.decode() if final else "{}"
        return Response({"status": "completed", "progress": 100, "result": final})

    return Response({"status": "running", "progress": int(progress)})
