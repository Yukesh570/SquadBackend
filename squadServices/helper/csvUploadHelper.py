# squadServices/views/vendor_rate_import_view.py

import json
import uuid
import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
import redis
import csv

from squadServices.helper.action import log_action_import
from squadServices.models.mappingSetup.mappingSetup import MappingSetup
from squadServices.models.notificationModel.notification import Notification
from squadServices.models.users import UserLog
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from drf_spectacular.utils import extend_schema, OpenApiParameter

redis_client = redis.StrictRedis.from_url(os.getenv("CELERY_RESULT_BACKEND"))

from squad.task import (
    import_country_task,
    import_currency_task,
    import_operator_network_code_task,
    import_operator_task,
    import_vendor_rate_task,
)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def country_csv(request):
    """
    Upload CSV and start Celery import task for Country model.
    """

    file = request.FILES.get("file")

    if not file:
        return Response({"error": "CSV file is required"}, status=400)
    if not file.name.lower().endswith(".csv"):
        return Response({"error": "Only CSV files are allowed"}, status=400)

    if file.content_type not in [
        "text/csv",
        "application/vnd.ms-excel",
    ]:
        return Response(
            {"error": "Invalid file type. Please upload a valid CSV file"}, status=400
        )
    # Save file temporarily
    filename = f"country_{uuid.uuid4().hex}.csv"
    temp_path = os.path.join(settings.MEDIA_ROOT, "imports")
    os.makedirs(temp_path, exist_ok=True)
    filepath = os.path.join(temp_path, filename)

    with open(filepath, "wb") as out:
        for chunk in file.chunks():
            out.write(chunk)

    task_id = uuid.uuid4().hex
    print("Starting country import with task ID:", task_id)
    # Trigger Celery task
    import_country_task.apply_async(
        args=[filepath, request.user.id, task_id], task_id=task_id
    )
    log_action_import(request.user, "Country")

    return Response({"message": "Import started", "task_id": task_id})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def operators_csv(request):
    """
    Upload CSV and start Celery import task for operator model.
    """

    file = request.FILES.get("file")
    if not file:
        return Response({"error": "CSV file is required"}, status=400)
    if not file.name.lower().endswith(".csv"):
        return Response({"error": "Only CSV files are allowed"}, status=400)

    if file.content_type not in [
        "text/csv",
        "application/vnd.ms-excel",
    ]:
        return Response(
            {"error": "Invalid file type. Please upload a valid CSV file"}, status=400
        )

    # Save file temporarily
    filename = f"operator_{uuid.uuid4().hex}.csv"
    temp_path = os.path.join(settings.MEDIA_ROOT, "imports")
    os.makedirs(temp_path, exist_ok=True)
    filepath = os.path.join(temp_path, filename)

    with open(filepath, "wb") as out:
        for chunk in file.chunks():
            out.write(chunk)

    task_id = uuid.uuid4().hex
    print("Starting operator import with task ID:", task_id)
    # Trigger Celery task
    import_operator_task.apply_async(
        args=[filepath, request.user.id, task_id], task_id=task_id
    )
    log_action_import(request.user, "Operator")

    return Response({"message": "Import started", "task_id": task_id})


@extend_schema(
    description=(
        "Upload CSV and start Celery import task for currency model.\n\n"
        "**Expected CSV Headers:**\n"
        "`name`, `currencyCode`, `numericCode`, `symbol`, `decimalPlaces`"
    ),
    request={
        "multipart/form-data": {
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "format": "binary",
                    "description": "CSV file containing currencies",
                }
            },
            "required": ["file"],
        }
    },
    responses={
        200: {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "task_id": {"type": "string"},
            },
        },
        400: {"type": "object", "properties": {"error": {"type": "string"}}},
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def currency_csv(request):
    """
    Upload CSV and start Celery import task for currency model.
    """

    file = request.FILES.get("file")
    if not file:
        return Response({"error": "CSV file is required"}, status=400)
    if not file.name.lower().endswith(".csv"):
        return Response({"error": "Only CSV files are allowed"}, status=400)

    if file.content_type not in [
        "text/csv",
        "application/vnd.ms-excel",
    ]:
        return Response(
            {"error": "Invalid file type. Please upload a valid CSV file"}, status=400
        )

    # Save file temporarily
    filename = f"currency_{uuid.uuid4().hex}.csv"
    temp_path = os.path.join(settings.MEDIA_ROOT, "imports")
    os.makedirs(temp_path, exist_ok=True)
    filepath = os.path.join(temp_path, filename)

    with open(filepath, "wb") as out:
        for chunk in file.chunks():
            out.write(chunk)

    task_id = uuid.uuid4().hex
    print("Starting currency import with task ID:", task_id)
    # Trigger Celery task
    import_currency_task.apply_async(
        args=[filepath, request.user.id, task_id], task_id=task_id
    )
    log_action_import(request.user, "Currency")

    return Response({"message": "Import started", "task_id": task_id})


onc_csv_file_param = openapi.Parameter(
    "file",
    in_=openapi.IN_FORM,
    description=(
        "Upload a CSV file to import Operator Network Codes.\n\n"
        "**Expected CSV Headers:**\n"
        "`operator_name`, `country_name`, `MCC`, `MNC`, `networkType`, `isPrimary`, `status`, `effectiveFrom`, `effectiveTo`, `notes`\n\n"
        "*(Note: Dates must be in YYYY-MM-DD format)*"
    ),
    type=openapi.TYPE_FILE,
    required=True,
)


# 2. Attach the swagger schema to your view (Must be above @api_view!)
@swagger_auto_schema(
    method="post",
    operation_description="Upload CSV and start Celery import task for Operator Network Code model.",
    manual_parameters=[onc_csv_file_param],
    consumes=["multipart/form-data"],
    responses={
        200: openapi.Response("Import started successfully"),
        400: openapi.Response("Bad Request (e.g., missing file, wrong format)"),
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def operatorNetworkCode_csv(request):
    """
    Upload CSV and start Celery import task for operator network code model.
    """

    file = request.FILES.get("file")
    if not file:
        return Response({"error": "CSV file is required"}, status=400)
    if not file.name.lower().endswith(".csv"):
        return Response({"error": "Only CSV files are allowed"}, status=400)

    if file.content_type not in [
        "text/csv",
        "application/vnd.ms-excel",
    ]:
        return Response(
            {"error": "Invalid file type. Please upload a valid CSV file"}, status=400
        )

    # Save file temporarily
    filename = f"operatorNetworkCode_{uuid.uuid4().hex}.csv"
    temp_path = os.path.join(settings.MEDIA_ROOT, "imports")
    os.makedirs(temp_path, exist_ok=True)
    filepath = os.path.join(temp_path, filename)

    with open(filepath, "wb") as out:
        for chunk in file.chunks():
            out.write(chunk)

    task_id = uuid.uuid4().hex
    print("Starting operator network code import with task ID:", task_id)
    # Trigger Celery task
    import_operator_network_code_task.apply_async(
        args=[filepath, request.user.id, task_id], task_id=task_id
    )
    log_action_import(request.user, "Operator Network Code")

    return Response({"message": "Import started", "task_id": task_id})


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
    log_action_import(request.user, "Vendor Rate")

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
        final_data = json.loads(final.decode() if final else "{}")

        if final_data.get("errors"):
            return Response(
                {
                    "status": "completed_with_errors",
                    "progress": 100,
                    "result": final_data,
                },
                status=400,
            )

        return Response({"status": "completed", "progress": 100, "result": final_data})

    return Response({"status": "running", "progress": int(progress)})
