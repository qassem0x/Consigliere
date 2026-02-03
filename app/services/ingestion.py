import pandas as pd
import os 
from fastapi import HTTPException
import uuid


def process_file(file_path: str):

    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
    elif file_path.endswith(".xlsx"):
        df = pd.read_excel(file_path)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use CSV or Excel.")

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace(r"[^\w]", "", regex=True)

    # Convert to PARQUET for higher speed 
    file_id = str(uuid.uuid4())
    parquet_filename = f"{file_id}.parquet"
    parquet_path = f"data/{parquet_filename}"

    df.to_parquet(parquet_path)

    os.remove(file_path)

    return {
        "file_id":file_id,
        "filename":parquet_filename,
        "rows":df.shape[0],
        "columns":list(df.columns),
        "preview": df.head(5).to_dict(orient="records")
    }