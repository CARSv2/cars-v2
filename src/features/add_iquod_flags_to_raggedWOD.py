# Load up each WOD ragged array netCDF file and add flags for iQuOD
# """
# The flags are contained in csv files with the following columns:
# - WOD unique cast identifier
# - iQuOD flag
# """
import logging
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import os
import pandas as pd
import xarray as xr
import pyarrow.dataset as pa_ds
import dask.dataframe as dd
from dask.distributed import Client


def write_flags_to_wod(flag_file, file_name, out_file):
    # open the netcdf file for this dataset
    ds = xr.open_dataset(file_name)
    # get the unique cast identifiers
    wod_unique_cast = ds['wod_unique_cast'].values
    # create a new array to hold the flags, that is the same size as the 'Temperature_WODflag' variable
    flags = ds['Temperature_WODflag'].copy()
    # create a new dataframe to hold the flags
    flags_df = pd.DataFrame(flags.values)
    # add a column to the dataframe for the cast identifier
    flags_df['wod_unique_cast'] = flags_df.index.get_level_values(0)
    # set these values to zero for now
    flags_df['wod_unique_cast'] = 0
    flags_df['depthNumber'] = 0
    flags_df['wod_unique_cast'] = flags_df['wod_unique_cast'].astype('int64')
    flags_df['depthNumber'] = flags_df['depthNumber'].astype('int64')
    # drop the old index
    flags_df = flags_df.reset_index(drop=True)
    # drop the first column
    flags_df = flags_df.drop(columns=0)
    # loop over the unique cast identifiers and add the cast identifier to the flags_df for the same number of z_row_size 
    start = 0
    for i, cast in enumerate(wod_unique_cast):
        # get the length of the cast
        length = ds['Temperature_row_size'][i].values
        # fill the wod_unique_cast column with the cast identifier from the start to start + length
        flags_df['wod_unique_cast'].values[start:start + int(length)] = cast
        # fill the depthNumber column from 0 to length for this cast
        flags_df['depthNumber'].values[start:start + int(length)] = range(0, int(length))
        # update the start index for the next cast
        start = start + int(length)
    # read the parquet file with pyarrow and filter it to only include the cast identifiers in the flags_df
    dataset = pa_ds.dataset(flag_file, format="parquet")
    df_filtered = dataset.to_table(filter=pa_ds.field('wod_unique_cast').isin(wod_unique_cast))
    # convert the filtered table to a pandas dataframe
    df_filtered = df_filtered.to_pandas()
    # merge the flags dataframe with the parquet dataframe on the cast identifier and depth number
    flags_df = flags_df.merge(df_filtered, on=['wod_unique_cast', 'depthNumber'], how='left')

    # Replace NaN values in the 'Temperature_IQuODflag' column with 0
    flags_df['Temperature_IQuODflag'] = flags_df['Temperature_IQuODflag'].fillna(0)
    # convert the 'Temperature_IQuODflag' column to int8
    flags_df['Temperature_IQuODflag'] = flags_df['Temperature_IQuODflag'].astype('int8')
    # remove the 'wod_unique_cast' and 'depthNumber' columns
    flags_df = flags_df.drop(columns=['wod_unique_cast', 'depthNumber'])
    # remove the index from the flags_df
    flags_df = flags_df.reset_index(drop=True)
    # convert the flags_df to a pandas dataframe
    # flags_df = flags_df.compute()
    # convert the flags_df['Temperature_IQuODflag'] column to an xarray data array with all the same dimensions as the original flags variable
    flags_da = xr.DataArray(flags_df['Temperature_IQuODflag'].values, dims=flags.dims, coords=flags.coords)
    # add the flags_da to the dataset as a new variable
    ds['Temperature_IQuODflag'] = flags_da
    # update the new variable attributes
    ds['Temperature_IQuODflag'].attrs['long_name'] = 'IQuOD quality flag for temperature'
    ds['Temperature_IQuODflag'].attrs['flag_values'] = '1, 2, 3, 4'
    ds['Temperature_IQuODflag'].attrs['flag_meanings'] = 'passed_all_tests High_True_Postive_Rate_test_failed Compromise_test_failed Low_False_Positive_test_failed'
    # update the global attributes for summary, id, creator_name, creator_email, project, date_created, date_modified, publisher_name, publisher_email, publisher_url, history
    ds.attrs['summary'] = 'Data for multiple casts from the World Ocean Database with IQuOD quality flags for temperature'
    ds.attrs['id'] = file_name + ',' + ds.attrs['id']
    ds.attrs['creator_name'] = ds.attrs['creator_name'] + ', ' + 'CSIRO Environment/Ocean Dynamics'
    ds.attrs['creator_email'] = ds.attrs['creator_email'] + ', ' + 'https://www.csiro.au/en/contact'
    ds.attrs['creator_url'] = ds.attrs['creator_url'] + ', ' + 'https://www.csiro.au'
    ds.attrs['project'] = ds.attrs['project'] + ', ' + 'IQuOD (International Quality-controlled Ocean Database)'
    ds.attrs['date_created'] = ds.attrs['date_created'] + ', ' + pd.Timestamp.now().strftime('%Y-%m-%dT%H:%M:%S')
    ds.attrs['date_modified'] = pd.Timestamp.now().strftime('%Y-%m-%dT%H:%M:%S')
    ds.attrs['publisher_name'] = ds.attrs['publisher_name'] + '; ' + 'CSIRO Environment/Ocean Dynamics'
    ds.attrs['publisher_email'] = ds.attrs['publisher_email'] + ', ' + 'https://www.csiro.au/en/contact'
    ds.attrs['publisher_url'] = ds.attrs['publisher_url'] + ', ' + 'https://www.csiro.au'
    ds.attrs['history'] = 'WOD downloaded on January 3, 2025 with IQuOD quality flags added to temperature variable'
    # put a cc4.0 license on the dataset
    ds.attrs['license'] = 'https://creativecommons.org/licenses/by/4.0/legalcode'
    # save the modified dataset
    ds.to_netcdf(out_file)
    logger.info(f"Saved new file with flags: {out_file}")


def convert_csv2parquet(csv_file, parquet_file):
    # start a dask client
    client = Client()
    # open the csv file for this dataset as a dataframe using
    df = dd.read_csv(csv_file, names=['wod_unique_cast', 'depthNumber','Temperature_IQuODflag'], header=None, dtype={'wod_unique_cast': 'int64', 'depthNumber': 'int64', 'Temperature_IQuODflag': 'int8'})
    # write the updated parquet file
    try:
        print(f'Saving Parquet file: {parquet_file}')
        df.to_parquet(parquet_file, compression='snappy')
        print(f'Successfully saved Parquet file: {parquet_file}')
    except Exception as e:
        print(f"Error saving Parquet file {parquet_file}: {e}")
    # close the dask client
    client.close()
    return


if __name__ == '__main__':
    """
    spin up cluster, concat, & write
    """
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)
    logger = logging.getLogger(__name__)
    # set up the input and output file paths
    folder = '/scratch/es60/rlc599/AQC_summaries'
    # list the datasets from the folder where datasets are the first three characters of the file names
    # datasets = sorted(set([f[:3] for f in os.listdir(folder) if f.endswith('.csv')]))
    # remove the XBT dataset from the list as we have already processed it
    # datasets.remove('XBT')
    datasets = ['XBT']
    WOD_path = '/scratch/es60/rlc599/WOD'
    out_path = '/scratch/es60/rlc599/IQuOD'
    # List only directories in WOD_path
    years = sorted([d for d in os.listdir(WOD_path) if os.path.isdir(os.path.join(WOD_path, d))])
    # remove years prior to 1992
    years = [year for year in years if int(year) >= 1992]
    # years = ['1966']
    # loop through the datasets
    for dataset in datasets:
        # if parquet files are not available, then create them
        flag_file = os.path.join(folder, dataset.lower() + '_flags.parquet')
        if not os.path.exists(flag_file):
            logger.info(f"Creating parquet file for {dataset}")
            # read the csv file for this dataset
            csv_file = os.path.join(folder, dataset + '_summary.csv')
            convert_csv2parquet(csv_file, flag_file)
        # loop through the years
        for year in years:
            # Open the netcdf file for this dataset
            file_name = os.path.join(WOD_path, year, 'wod_' + dataset.lower() + '_' + year + '.nc')
            if not os.path.exists(file_name):
                logger.info(f"File not found: {file_name}")
                continue
            # create the output file name
            out_file = os.path.join(out_path, year, 'iquod_' + dataset.lower() + '_' + year + '_iquodflags.nc')
            # check if the output path exists, if not create it
            out_dir = os.path.dirname(out_file)
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            # write the flags to the parquet files
            logger.info(f"Writing flags to file: {file_name}")
            write_flags_to_wod(flag_file, file_name, out_file)