import pandas as pd
import os
import logging
from fastapi import HTTPException
import uuid

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _transform_to_parquet(temp_file_path: str, original_filename: str):
    try:
        if temp_file_path.endswith(".csv"):
            df = pd.read_csv(temp_file_path)
        elif temp_file_path.endswith(".xlsx"):
            df = pd.read_excel(temp_file_path)
        else:
            raise ValueError("Unsupported format. Please upload CSV or Excel.")

        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace(r"[^\w]", "", regex=True)
        )

        file_uuid = str(uuid.uuid4())
        parquet_filename = f"{file_uuid}.parquet"

        os.makedirs("data", exist_ok=True)
        parquet_path = f"data/{parquet_filename}"

        df.to_parquet(parquet_path, index=False)

        metadata = {
            "file_id": file_uuid,
            "filename": parquet_filename,
            "rows": df.shape[0],
            "columns": list(df.columns),
        }

        logger.info(f"Transformed {original_filename} to {parquet_filename}")
        return metadata

    except Exception as e:
        logger.error(f"Error transforming file {original_filename}: {e}")
        raise e
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
