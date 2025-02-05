import os
import pandas as pd


def write_flags_to_parquet(folder, datasets, CODA_path):
    # loop through the datasets and each OBS/year folder to access the failure.json.tar.gz files
    for dataset in datasets:
        # list the years
        # open the csv file for this dataset as a dataframe
        csv_file = os.path.join(folder, dataset + '_summary.csv')
        df = pd.read_csv(csv_file)
        # add column names to the dataframe
        df.columns = ['castNumber', 'depthNumber','iquodFlags']
        # get the years information from the CODA path
        years = sorted(os.listdir(CODA_path))
        for year in years:
            # load the parquet file for this dataset and this year
            file_name = os.path.join(CODA_path, year, 'WOD2018_CODA_' + year + '_' + dataset.lower() + '.parquet')
            file_name_out = os.path.join(CODA_path, year, 'WOD2018_CODA_' + year + '_' + dataset.lower() + '_iquodflags.parquet')
            if os.path.exists(file_name):
                print('Opening Parquet file: ', file_name)
                wod_dataframe = pd.read_parquet(os.path.join(CODA_path,str(year),file_name), engine='fastparquet')
                # sort the dataframe by 'wod_unique_cast' and 'z'
                wod_dataframe = wod_dataframe.sort_values(by=['wod_unique_cast', 'z'])
                # create a new column called 'Temperature_iquodflag'
                if "Temperature_iquodflag" not in wod_dataframe.columns:
                    wod_dataframe['Temperature_iquodflag'] = 0
                # create a new column called 'depthNumber' where the smallest depth is 0 and the largest depth is len(depth) for each cast
                if "depthNumber" not in wod_dataframe.columns:
                    wod_dataframe['depthNumber'] = wod_dataframe.groupby('wod_unique_cast').cumcount()
            else:
                continue
            # create a new co
            # merge the dataframes on 'castNumber' and 'depthNumber'
            df = df.sort_values(by=['castNumber', 'depthNumber'])
            wod_dataframe = wod_dataframe.merge(df, on=['castNumber', 'depthNumber'], how='left')


            # write the updated parquet file
            wod_dataframe.to_parquet(file_name_out)

# set up the input and output file paths
folder = '/Users/cow074/code/IQuOD/AQC_flag_summaries'
# list the subdirectories to get the dataset names
# datasets = sorted(os.listdir(folder))
datasets = ['XBT']
CODA_path = '/Volumes/observations/CARSv2_ancillary/CODA/CODAv1/parquet'

# write the flags to the parquet files
write_flags_to_parquet(folder, datasets, CODA_path)


