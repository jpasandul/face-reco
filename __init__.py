import logging
import azure.functions as func

def main(myblob: func.InputStream):
    try:
        # Read the blob content once
        content = myblob.read()
        size = len(content)
        
        logging.info(f"Python blob trigger function processed blob:\n"
                     f"Name: {myblob.name}\n"
                     f"Blob Size: {size} bytes")
        
        # For testing purposes, save the image to a temporary directory
        # (on Linux-based systems, /tmp/ is writable)
        file_name = f"/tmp/{myblob.name.split('/')[-1]}"
        with open(file_name, "wb") as f:
            f.write(content)
        logging.info(f"Image saved to local path: {file_name}")
        
        # Return a success log (Note: blob-triggered functions do not return an HTTP response)
        logging.info("Blob processing completed successfully")
        
    except Exception as e:
        logging.error(f"Error processing blob: {e}") 