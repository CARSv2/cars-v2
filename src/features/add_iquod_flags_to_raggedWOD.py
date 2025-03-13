# Load up each WOD ragged array netCDF file and add flags for iQuOD
# """
# The flags are contained in csv files with the following columns:
# - WOD unique cast identifier
# - iQuOD flag
# """

import os
import pandas as pd
import xarray as xr
import dask.dataframe as dd
from dask.distributed import Client
import dask

def write_flags_to_wod(df, file_name):
    # open the netcdf file for this dataset
    ds = xr.open_dataset(file_name)
    # get the unique cast identifiers
    wod_unique_cast = ds['wod_unique_cast'].values
    # create a new array to hold the flags, that is the same size as the 'Temperature_WODflag' variable
    flags = ds['Temperature_WODflag'].copy()
    # change the flags values to all zeros
    flags.values = flags.values * 0
    start = 0
    # loop through the unique cast identifiers
    for i, cast in enumerate(wod_unique_cast):
        # get the indices of the rows in the dataframe that match this cast
        rows = df[df['wod_unique_cast'] == cast]
        # if there are no rows in the dataframe for this cast, then skip
        if len(rows) == 0:
            continue
        # get the indices of flags that correspond to this cast
        ndeps = ds['Temperature_row_size'][i].values
        # start is the index of the first Temperature_IQuODflag value for this cast and end is the final index
        end = start + ndeps
        # get the flags for this cast
        cast_flags = rows['Temperature_iquodflag'].values
        # update the flags array with the new flags
        flags.values[start:end] = cast_flags
        # update the start index for the next cast
        start = end

    # add the new variable to the dataset
    ds['Temperature_IQuODflag'] = flags
    # update the new variable attributes
    ds['Temperature_IQuODflag'].attrs['long_name'] = 'IQuOD quality flag for temperature'
    ds['Temperature_IQuODflag'].attrs['flag_values'] = '1, 2, 3, 4'
    ds['Temperature_IQuODflag'].attrs['flag_meanings'] = 'passed_all_tests High_True_Postive_Rate_test_failed Compromise_test_failed Low_False_Positive_test_failed'
    # save the modified dataset
    new_file_name = file_name.replace('.nc', '_iquodflags.nc')
    ds.to_netcdf(new_file_name)


def convert_csv2parquet(csv_file, parquet_file):
    # Set Dask configuration for shuffle method and memory limit
    dask.config.set({'dataframe.shuffle.method': 'disk', 'distributed.worker.memory.target': 0.8,
                     'distributed.worker.memory.spill': 0.9})
    # open the csv file for this dataset as a dataframe
    df = dd.read_csv(csv_file)
    # add column names to the dataframe
    df.columns = ['wod_unique_cast', 'depthNumber','Temperature_iquodflag']
    df = df.sort_values(by=['wod_unique_cast', 'depthNumber'])
    # optimise data types
    df['wod_unique_cast'] = df['wod_unique_cast'].astype('int64')
    df['depthNumber'] = df['depthNumber'].astype('int64')
    df['Temperature_iquodflag'] = df['Temperature_iquodflag'].astype('int8')
    # write the updated parquet file
    try:
        print(f'Saving Parquet file: {parquet_file}')
        df.to_parquet(parquet_file, compression='snappy')
        print(f'Successfully saved Parquet file: {parquet_file}')
    except Exception as e:
        print(f"Error saving Parquet file {parquet_file}: {e}")
    return df


if __name__ == '__main__':
    # open dask client
    client = Client(processes=False)  # Start a Dask client
    # set up the input and output file paths
    folder = '/Users/cow074/code/IQuOD/AQC_flag_summaries'
    # list the datasets
    datasets = ['XBT']
    WOD_path = '/Users/cow074/code/IQuOD/WODdata'
    # get a list of years from the subdirectories in the WOD path
    years = sorted(os.listdir(WOD_path))
    # loop through the datasets
    for dataset in datasets:
        # if parquet files are not available, then create them
        if not os.path.exists(os.path.join(folder, dataset.lower() + '_flags.parquet')):
            csv_file = os.path.join(folder, dataset + '_summary.csv')
            parquet_file = os.path.join(folder, dataset.lower() + '_flags.parquet')
            df = convert_csv2parquet(csv_file, parquet_file)
        else:
            df = dd.read_parquet(os.path.join(folder, dataset.lower() + '_flags.parquet'))
        # loop through the years
        for year in years:
            # Open the netcdf file for this dataset
            file_name = os.path.join(WOD_path, year, 'wod_' + dataset + '.nc')
            if not os.path.exists(file_name):
                continue
            # write the flags to the parquet files
            write_flags_to_wod(df, file_name)
    # close the Dask client
    client.close()