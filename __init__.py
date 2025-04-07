import azure.functions as func
import logging
from datetime import datetime

app = func.FunctionApp()

@app.blob_trigger(arg_name="myblob", path="face-images/{name}", connection="AzureWebJobsStorage")
def BlobTriggerImageUpload(myblob: func.InputStream):
    try:
        logging.info(f"✅ Function running in AZURE CLOUD - Timestamp: {datetime.now()}")
        blob_name = myblob.name
        blob_size = myblob.length

        logging.info(f"✅ Blob Trigger Activated")
        logging.info(f"📂 Blob Name: {blob_name}")
        logging.info(f"📏 Blob Size: {blob_size} bytes")

        # Optionally, read the first few bytes to confirm the file type
        content = myblob.read(1024)  # Read the first 1KB for inspection
        logging.info(f"🔍 First 1KB of Blob Data: {content[:50]}...")  # Log a sample of the content

    except Exception as e:
        logging.error(f"❌ Error processing blob: {str(e)}")
