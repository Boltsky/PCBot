import os
import shutil
import logging
from security_manager import validate_deletion
from telegram_bot import send_status_update

def secure_delete(path):
    try:
        # Validate with security_manager
        if not validate_deletion(path):
            raise PermissionError("Deletion not permitted by security policy.")

        # Check if path is a file or directory
        if os.path.isfile(path):
            os.remove(path)
            operation = "file"
        elif os.path.isdir(path):
            shutil.rmtree(path)
            operation = "directory"
        else:
            raise FileNotFoundError(f"The path {path} does not exist.")

        # Log the event
        logging.info(f"{operation.capitalize()} '{path}' deleted successfully.")
        
        # Send status update
        send_status_update(f"{operation.capitalize()} '{path}' deleted successfully.")
    
    except Exception as e:
        # Handle errors and log
        logging.error(f"Error deleting {path}: {e}")
        
        # Send error status update
        send_status_update(f"Error deleting {path}: {e}")

# Example usage
# secure_delete("/path/to/file_or_directory")

