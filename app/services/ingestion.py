import pandas as pd
import os
from fastapi import HTTPException
import uuid


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
            "filename": parquet_filename,  # The system name (UUID.parquet)
            "rows": df.shape[0],
            "columns": list(df.columns),
        }

        return metadata

    except Exception as e:
        raise e
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
