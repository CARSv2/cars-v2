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

def write_flags_to_wod(df, file_name, file_name_out, wod_unique_cast_df):
    # open the netcdf file for this dataset
    ds = xr.open_dataset(file_name)
    # get the unique cast identifiers
    wod_unique_cast = ds['wod_unique_cast'].values
    # if none of the wod_unique_cast values are included in wo_unique_cast_df, then return
    if len(set(wod_unique_cast).intersection(set(wod_unique_cast_df))) == 0:
        print(f'No matching unique cast identifiers found in {file_name}')
        return
    # create a new array to hold the flags, that is the same size as the 'Temperature_WODflag' variable
    ds['Temperature_IQuODflag'] = ds['Temperature_WODflag'].copy()
     # change the flags values to all zeros
    ds['Temperature_IQuODflag'].values = ds['Temperature_IQuODflag'].values * 0   # convert flags to a dataframe
    flags = ds['Temperature_IQuODflag'].to_dataframe()
    # add the wod_unique_cast column ready to add the unique cast identifiers
    flags['wod_unique_cast'] = 0
    # add a column to hold the depth number
    flags['depthNumber'] = 0
    start = 0
    # loop through the unique cast identifiers
    for i, cast in enumerate(wod_unique_cast):
        # get the indices of flags that correspond to this cast
        ndeps = ds['Temperature_row_size'][i].values
        # start is the index of the first Temperature_IQuODflag value for this cast and end is the final index
        end = start + int(ndeps)
        # display the depths for this cast as a check
        #depths = ds['z'][start:end].values
        #print(f'Cast: {cast}, Depths: {depths}')
        # fill the wod_unique_cast column with the cast identifier
        flags['wod_unique_cast'].values[start:end] = cast
        # fill the depthNumber column with the depth number
        flags['depthNumber'].values[start:end] = range(int(ndeps))
        # update the start index for the next cast
        start = end

    # merge the dataframes on 'wod_unique_cast' and 'depthNumber'
    flags_merged = dd.merge(flags, df, on=['wod_unique_cast', 'depthNumber'], how='left') 
    
    # convert the dataframe column 'Temperature_iquodflag' back to an xarray dataarray variable
    flags_out = flags_merged.compute()
    # Create a mapping for the order of 'wod_unique_cast' in the dataset
    order_mapping = {cast: idx for idx, cast in enumerate(ds['wod_unique_cast'].values)}
    # Add a temporary column for sorting
    flags_out['order'] = flags_out['wod_unique_cast'].map(order_mapping)
    # Sort the dataframe by the 'order' column
    flags_out = flags_out.sort_values(by=['order', 'depthNumber']).drop(columns=['order'])
    # Assign the values
    ds['Temperature_IQuODflag'].values = flags_out['Temperature_iquodflag'].values
    # update the new variable attributes
    ds['Temperature_IQuODflag'].attrs['long_name'] = 'IQuOD quality flag for temperature'
    ds['Temperature_IQuODflag'].attrs['flag_values'] = '0, 1, 2, 3, 4'
    ds['Temperature_IQuODflag'].attrs['flag_meanings'] = 'no_tests_performed passed_all_tests High_True_Postive_Rate_test_failed Compromise_test_failed Low_False_Positiv
e_test_failed'
    # update the fill value to -9b
    ds['Temperature_IQuODflag'].encoding['_FillValue'] = -9
    # create the output directory if it does not exist
    os.makedirs(os.path.dirname(file_name_out), exist_ok=True)
    # save the modified dataset
    ds.to_netcdf(file_name_out)

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
    folder = '/scratch3/cow074/AQC_flag_summaries'
    # list the datasets
    datasets = ['XBT']
    WOD_path = '/datasets/work/soop-xbt/work/WOD'
    WOD_path_out = '/datasets/work/soop-xbt/work/IQuOD'
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
        # get the unique cast identifiers from the dataframe
        wod_unique_cast_df = df['wod_unique_cast'].unique().compute().tolist()
        # loop through the years
        for year in years:
            # Open the netcdf file for this dataset
            file_name = os.path.join(WOD_path, year, 'wod_' + dataset.lower() + '_' + year + '.nc')
            if not os.path.exists(file_name):
                print(f'File {file_name} does not exist')
                continue
            print(f'Processing file: {file_name}')
            # create the path to the new file out if required
            new_file_name = file_name.replace('wod', 'iquod')
            file_name_out = os.path.join(WOD_path_out, year, os.path.basename(new_file_name))
            # write the flags to the parquet files
            write_flags_to_wod(df, file_name, file_name_out, wod_unique_cast_df)
    # close the Dask client
    client.close()

