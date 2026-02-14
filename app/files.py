import os
import shutil

from config import UPLOAD_FOLDER, RESULT_FOLDER

def delete_files(files: list):
    try:
        for filename in files:
            # print(file)
            try:
                path_to_uploaded_file = os.path.join(UPLOAD_FOLDER, filename)
                os.remove(path_to_uploaded_file)
            except Exception:
                pass
            
            try:
                path_to_img_result_folder = os.path.join(RESULT_FOLDER, filename)
                shutil.rmtree(path_to_img_result_folder)
            except Exception:
                pass

        return {
            "success": True,
            "msg": "All files have been deleted."
        }
    except Exception as exc_msg:
        return {
            "success": False,
            "err_msg": str(exc_msg)
        }