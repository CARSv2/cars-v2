import os
import dask.dataframe as dd
from dask.distributed import Client

def write_flags_to_parquet(folder, datasets, CODA_path):
    client = Client()  # Start a Dask client
    # loop through the datasets and each OBS/year folder to access the failure.json.tar.gz files
    for dataset in datasets:
        # list the years
        # open the csv file for this dataset as a dataframe
        csv_file = os.path.join(folder, dataset + '_summary.csv')
        df = dd.read_csv(csv_file)     
        # add column names to the dataframe
        df.columns = ['wod_unique_cast', 'depthNumber','Temperature_iquodflag']       
        df = df.sort_values(by=['wod_unique_cast', 'depthNumber'])
        # optimise data types
        df['wod_unique_cast'] = df['wod_unique_cast'].astype('int64')
        df['depthNumber'] = df['depthNumber'].astype('int64')
        df['Temperature_iquodflag'] = df['Temperature_iquodflag'].astype('int8')
        # get the years information from the CODA path
        #years = sorted(os.listdir(CODA_path))
        years = ['2000']
        for year in years:
            # load the parquet file for this dataset and this year
            file_name = os.path.join(CODA_path, year, 'WOD2018_CODA_' + year + '_' + dataset.lower() + '.parquet')
            file_name_out = os.path.join(CODA_path, year, 'WOD2018_CODA_' + year + '_' + dataset.lower() + '_iquodflags')
            if os.path.exists(file_name):
                print('Opening Parquet file: ', file_name)
                wod_dataframe = dd.read_parquet(os.path.join(CODA_path,str(year),file_name))
                # sort the dataframe by 'wod_unique_cast' and 'z'
                wod_dataframe = wod_dataframe.sort_values(by=['wod_unique_cast', 'z'])
                # create a new column called 'depthNumber' where the smallest depth is 0 and the largest depth is len(depth) for each cast
                if "depthNumber" not in wod_dataframe.columns:
                    wod_dataframe['depthNumber'] = wod_dataframe.groupby('wod_unique_cast').cumcount()
            else:
                continue
            # merge the dataframes on 'wod_unique_cast' and 'depthNumber'
            wod_dataframe = wod_dataframe.merge(df, on=['wod_unique_cast', 'depthNumber'], how='left')

            # write the updated parquet file
            wod_dataframe.to_parquet(file_name_out, file_name='file_name_out', compression='snappy')
    client.close()  # Close the Dask client

if __name__ == '__main__':       
    # set up the input and output file paths
    folder = '/scratch3/cow074/AQC_flag_summaries'
    # list the subdirectories to get the dataset names
    # datasets = sorted(os.listdir(folder))
    datasets = ['XBT']
    CODA_path = '/scratch3/cow074/CODAv1/parquet'

    # write the flags to the parquet files
    write_flags_to_parquet(folder, datasets, CODA_path)