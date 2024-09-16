import pandas as pd
import pyarrow as pa

import pyarrow.parquet as pq

df = pd.read_csv('data/cars.csv')

byte_string_columns = ddf.select_dtypes(include=[object]).applymap(lambda x: isinstance(x, bytes)).any()
byte_string_columns = byte_string_columns[byte_string_columns].index.tolist()
print(byte_string_columns)

# Function to convert byte strings to regular strings
def remove_binary_prefix(val):
    if isinstance(val, bytes):  # check if the value is bytes
        return val.decode('utf-8')  # decode bytes to string
    return val

# Apply the function to all elements in the DataFrame
df_cleaned = df.map(remove_binary_prefix)

ddf = dd.from_pandas(df_cleaned, npartitions=10)

# Convert byte string columns to regular string columns in ddf
ddf_cleaned = ddf.map_partitions(lambda df: df.applymap(remove_binary_prefix))

# Print the first few rows of the cleaned DataFrame 
print(ddf_cleaned.head())

# Save the cleaned DataFrame as a Parquet file
pq.write_table(pa.Table.from_pandas(ddf_cleaned.compute()), 'data/cars_cleaned.parquet')