import pandas as pd
from premia import db
from premia.data import DataError


def copy(
    file_path: str,
    table_name: str | None = None,
) -> pd.DataFrame:
    df = pd.read_csv(file_path)

    if table_name:
        try:
            df.to_sql(
                table_name,
                con=db.connect(),
                if_exists="append",
                index=False,
            )
        except Exception as e:
            raise DataError(
                f"Failed to copy CSV data to table '{table_name}': {e}"
            )

    return df
