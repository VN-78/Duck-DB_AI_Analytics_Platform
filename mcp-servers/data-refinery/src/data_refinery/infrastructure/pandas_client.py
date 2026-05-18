# region imports
import pandas as pd
# import io
import os
import logging
from typing import Any, Tuple, Optional, List, Dict, cast
# from urllib.parse import urlparse

# Domain Imports
from data_refinery.domain.interfaces.repository import IDatasetRepository
from data_refinery.domain.models.dataset import DatasetOverview, ColumnProfile
from data_refinery.domain.models.cleaning import CleaningOptions

logger = logging.getLogger(__name__)

# region load_data  
class PandasDatasetClient(IDatasetRepository):
    """
    Implementation to load Data from both local files and S3 URLs using pandas as the engine
    """
    
    def _get_storage_options(self) -> Optional[Dict[str, Any]]:
        """Returns storage options for s3fs/boto3 if S3 config is present in env."""
        endpoint = os.environ.get("S3_ENDPOINT_URL")
        key = os.environ.get("S3_ACCESS_KEY")
        secret = os.environ.get("S3_SECRET_KEY")
        
        if endpoint and key and secret:
            logger.info(f"Setting storage options for S3. Endpoint: {endpoint}")
            return {
                "client_kwargs": {"endpoint_url": endpoint},
                "key": key,
                "secret": secret
            }
        logger.warning("S3 environment variables missing. Storage options not set.")
        return None

    def load_data(self, file_uri: str) -> pd.DataFrame:
        """
        Smart loader: checks if URI is S3 or Local, and handles CSV or Parquet.
        """
        logger.info(f"Pandas loading data from: {file_uri}")
        storage_opts = self._get_storage_options() if file_uri.startswith("s3://") else None
        
        try:
            if file_uri.endswith(".parquet"):
                df = pd.read_parquet(file_uri, storage_options=storage_opts)
            else:
                # Default to CSV
                df = pd.read_csv(file_uri, storage_options=storage_opts)
            
            logger.info(f"Successfully loaded {len(df)} rows from {file_uri}")
            return df
        except Exception as e:
            logger.error(f"Pandas failed to load {file_uri}: {e}")
            raise

    def save_dataframe(self, df: pd.DataFrame, file_uri: str) -> None:
        """
        Smart saver: saves to local or S3 based on URI.
        """
        logger.info(f"Saving dataframe ({len(df)} rows) to: {file_uri}")
        try:
            if file_uri.startswith("s3://"):
                storage_opts = self._get_storage_options()
                df.to_parquet(file_uri, storage_options=storage_opts)
            else:
                # Ensure parent dir exists for local files
                os.makedirs(os.path.dirname(file_uri), exist_ok=True)
                df.to_parquet(file_uri)
            logger.info(f"Successfully saved file to {file_uri}")
        except Exception as e:
            logger.error(f"Failed to save file to {file_uri}: {e}")
            raise
# endregion

# region analyze data 

    def analyze(self, df: pd.DataFrame) -> DatasetOverview:
        """
        The 'Business Logic'. 
        Converts raw DataFrame -> Clean Domain Model.
        """
        columns: List[ColumnProfile] = []
        
        # Iterate by index to avoid issues with duplicate column names
        for i in range(len(df.columns)):
            col_name = df.columns[i]
            series = df.iloc[:, i]
            
            # 1. Map Pandas Dtypes to simple strings
            dtype = str(series.dtype)
            
            # 2. Calculate Missing %
            missing_sum = series.isnull().sum()
            missing_count = int(cast(Any, missing_sum))
            total_count = len(df)
            missing_pct = (missing_count / total_count) * 100 if total_count > 0 else 0.0

            # 3. Calculate Stats for Numeric Columns
            mean_val: Optional[float] = None
            std_val: Optional[float] = None
            min_val: Optional[float] = None
            max_val: Optional[float] = None
            outlier_count: Optional[int] = None

            if pd.api.types.is_numeric_dtype(series):
                # Calculate basic stats (convert to native python float for JSON serialization)
                try:
                    s_mean = series.mean()
                    s_std = series.std()
                    s_min = series.min()
                    s_max = series.max()

                    # Use cast to satisfy type checker that these are scalars
                    mean_val = float(cast(Any, s_mean)) if not pd.isna(s_mean) else None
                    std_val = float(cast(Any, s_std)) if not pd.isna(s_std) else None
                    min_val = float(cast(Any, s_min)) if not pd.isna(s_min) else None
                    max_val = float(cast(Any, s_max)) if not pd.isna(s_max) else None
                    
                    # Calculate Outliers (IQR Method)
                    # We drop NAs for quantile calculation to avoid issues
                    valid_data = series.dropna()
                    if not valid_data.empty:
                        q1_val = valid_data.quantile(0.25)
                        q3_val = valid_data.quantile(0.75)
                        Q1 = float(cast(Any, q1_val))
                        Q3 = float(cast(Any, q3_val))
                        IQR = Q3 - Q1
                        lower_bound = Q1 - 1.5 * IQR
                        upper_bound = Q3 + 1.5 * IQR
                        
                        # Count values outside bounds
                        outliers = valid_data[(valid_data < lower_bound) | (valid_data > upper_bound)]
                        outlier_count = int(len(outliers))
                except Exception:
                    # Fallback for edge cases (e.g. all NaNs or mixed types that tricked the check)
                    pass

            columns.append(ColumnProfile(
                name=str(col_name),
                data_type=dtype,
                missing_percentage=round(float(cast(Any, missing_pct)), 2),
                mean=mean_val,
                std=std_val,
                min=min_val,
                max=max_val,
                outlier_count=outlier_count
            ))

        # 4. Create Sample Rows (handle NaN values for JSON safety)
        # replace(float('nan'), None) ensures JSON compatibility
        sample = df.head(5).replace({float('nan'): None}).to_dict(orient='records')

        return DatasetOverview(
            total_rows=len(df),
            total_columns=len(df.columns),
            columns=columns,
            sample_data=sample
        )
# endregion

# region clean data 

    def clean_dataset(self, df: pd.DataFrame, options: CleaningOptions) -> Tuple[pd.DataFrame, DatasetOverview]:
        """
        Applies cleaning rules to the dataset.
        Returns the cleaned DataFrame and its new quality overview.
        """
        # 1. Normalize Headers (Global Rule)
        if options.normalize_headers:
            # - Strip whitespace
            # - Lowercase
            # - Replace spaces with underscores
            # - Remove special characters (keep only alphanumeric and underscores)
            new_cols = (df.columns
                .str.strip()
                .str.lower()
                .str.replace(r'\s+', '_', regex=True)
                .str.replace(r'[^\w]', '', regex=True))
            
            # Handle duplicates
            counts: Dict[str, int] = {}
            final_columns = []
            for col in new_cols:
                if col in counts:
                    counts[col] += 1
                    final_columns.append(f"{col}_{counts[col]}")
                else:
                    counts[col] = 0
                    final_columns.append(col)
            
            df.columns = pd.Index(final_columns)

        # 2. Date Normalization
        if options.date_columns:
            for date_cfg in options.date_columns:
                col = date_cfg.column_name
                if col in df.columns:
                    try:
                        # Convert to datetime objects first (handles various input formats)
                        # errors='coerce' turns unparseable strings into NaT
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                        
                        # Apply target string format
                        # Note: This converts the column to Object/String type
                        if date_cfg.output_format:
                            # Use .dt accessor explicitly
                            df[col] = df[col].dt.strftime(date_cfg.output_format)
                    except Exception:
                        # If a column is completely incompatible, we skip it to prevent crashing
                        pass

        # 3. Apply Column-Specific Strategies
        for column, strategy in options.strategies.items():
            if column not in df.columns:
                continue  # Skip columns that don't exist (safety check)

            # Strategy: DROP ROW
            if strategy == "drop":
                df = df.dropna(subset=[column])

            # Strategy: FILL ZERO
            elif strategy == "zero":
                # Only apply to numeric columns to prevent errors
                if pd.api.types.is_numeric_dtype(df[column]):
                    df[column] = df[column].fillna(0)

            # Strategy: FILL MEAN
            elif strategy == "mean":
                if pd.api.types.is_numeric_dtype(df[column]):
                    mean_val = df[column].mean()
                    df[column] = df[column].fillna(mean_val)

            # Strategy: FILL MODE (Most Frequent)
            elif strategy == "mode":
                # mode() returns a Series (there can be ties), so we take the first one ([0])
                col_mode = df[column].mode()
                if not col_mode.empty:
                    mode_val = col_mode.iloc[0]
                    df[column] = df[column].fillna(mode_val)

            # Strategy: FILL UNKNOWN
            elif strategy == "unknown":
                # Usually for text columns
                df[column] = df[column].fillna("Unknown")

        # 4. Generate Quality Report for the Cleaned Data
        overview = self.analyze(df)

        return df, overview
# endregion