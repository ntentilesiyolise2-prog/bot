from fastapi import APIRouter, UploadFile, File
import json
import zipfile
import io
import os

router = APIRouter()

@router.get("/api/export_settings")
async def export_settings():
    # Create ZIP with config.json and .env
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        if os.path.exists('config.json'):
            zip_file.write('config.json')
        if os.path.exists('.env'):
            zip_file.write('.env')
    zip_buffer.seek(0)
    return Response(zip_buffer.read(), media_type="application/zip", headers={"Content-Disposition": "attachment; filename=settings.zip"})

@router.post("/api/import_settings")
async def import_settings(file: UploadFile = File(...)):
    contents = await file.read()
    zip_buffer = io.BytesIO(contents)
    with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
        zip_file.extractall('.')
    return {"status": "settings imported"}
