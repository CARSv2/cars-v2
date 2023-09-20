import datetime as dt
import gsw
import os
import sys
import pandas as pd
import numpy as np
from netCDF4 import Dataset, date2num
from generate_netcdf_att import generate_netcdf_att, get_imos_parameter_info


def convert_txt2nc(MNF_data_path):
    # set up dictionaries to map the cast dimensioned names to the MNF names
    imosnames = ['TEMP', 'PSAL', 'DOXY', 'FLU2', 'PAR', 'CDOM', 'TRANS']
    mnfnames = ['TEMPERATURE', 'SALINITY', 'OXYGEN', 'FLUORESCENCE', 'PAR', 'CDOM', 'TRANSMITTANCE']
    vardict = dict(zip(mnfnames, imosnames))
    print(vardict)
    imosglobnames = ['cruise', 'station', 'project', 'site_code', 'unique_code']
    mnfglobnames = ['SURVEY_NAME', 'CAST_NO', 'SURVEY_NAME', 'MARLIN_ID', 'MARLIN_UUID']
    globdict = dict(zip(mnfglobnames, imosglobnames))
    print(globdict)

    # read a file with the global attributes included and the nc configuration file
    conf_file_generic = '/Users/cow074/code/CARS/cars-v2/src/features/IMOScode/generate_nc_file_attMNF'

    # FLAGS
    #
    #     Will do a flag conversion to IMOS flags, final column
    #     State        Unsigned Byte          Signed Byte         IMOS equivalent
    #     Good         0 ≤ flag ≤ 63          0 ≤ flag ≤ 63       1
    #     Suspect      64 ≤ flag ≤ 127        64 ≤ flag ≤ 127     3
    #     Bad          128 ≤ flag ≤ 191       -128 ≤ flag ≤ -65   4
    #     No QC        192 ≤ flag ≤ 255       -64 ≤ flag ≤ -1     0
    #

    # two files, one is the station information ('ctd_header.tsv') other is the data ('ctd_data.tsv')
    # link is the data_id field
    # now let's read in the CTD data from the Oracle database

    filn = MNF_data_path + '/ctd_data.tsv'  # read the data file
    filnh = MNF_data_path + '/ctd_header.tsv' # read the header file

    # read the data:
    df = pd.read_csv(filn, sep='\t')
    # read the header file:
    dfheads = pd.read_csv(filnh, sep='\t')

    # convert the oxygen concentration from umole/L to mole/m-3
    # IF DOING HERE, is on ENTIRE dataset. More efficient to do it here.
    # assign back to dataframe
    df.loc[df['PARAMETER_CODE'] == 'OXYGEN', 'VALUE'] \
        = df.loc[df['PARAMETER_CODE'] == 'OXYGEN', 'VALUE'] * 1e-3

    # map flag values to IMOS flags
    df.loc[np.logical_and(df['QC_FLAG'] >= 0, df['QC_FLAG'] <= 63), 'QC_FLAG'] = 1
    df.loc[np.logical_and(df['QC_FLAG'] >= 64, df['QC_FLAG'] <= 127), 'QC_FLAG'] = 3
    df.loc[np.logical_and(df['QC_FLAG'] >= 128, df['QC_FLAG'] <= 191), 'QC_FLAG'] = 4
    df.loc[np.logical_and(df['QC_FLAG'] >= 192, df['QC_FLAG'] <= 255), 'QC_FLAG'] = 0
    df.loc[np.isnan(df['QC_FLAG']), 'QC_FLAG'] = 9  # missing value

    dfheads.loc[np.logical_and(dfheads['POSITION_QC_FLAG'] >= 0, dfheads['POSITION_QC_FLAG'] <= 63), 'POSITION_QC_FLAG'] = 1
    dfheads.loc[np.logical_and(dfheads['POSITION_QC_FLAG'] >= 64, dfheads['POSITION_QC_FLAG'] <= 127), 'POSITION_QC_FLAG'] = 3
    dfheads.loc[np.logical_and(dfheads['POSITION_QC_FLAG'] >= 128, dfheads['POSITION_QC_FLAG'] <= 191), 'POSITION_QC_FLAG'] = 4
    dfheads.loc[np.logical_and(dfheads['POSITION_QC_FLAG'] >= 192, dfheads['POSITION_QC_FLAG'] <= 255), 'POSITION_QC_FLAG'] = 0
    dfheads.loc[np.isnan(dfheads['POSITION_QC_FLAG']), 'POSITION_QC_FLAG'] = 9  # missing value

    dfheads.loc[np.logical_and(dfheads['TIME_QC_FLAG'] >= 0, dfheads['TIME_QC_FLAG'] <= 63), 'TIME_QC_FLAG'] = 1
    dfheads.loc[np.logical_and(dfheads['TIME_QC_FLAG'] >= 64, dfheads['TIME_QC_FLAG'] <= 127), 'TIME_QC_FLAG'] = 3
    dfheads.loc[np.logical_and(dfheads['TIME_QC_FLAG'] >= 128, dfheads['TIME_QC_FLAG'] <= 191), 'TIME_QC_FLAG'] = 4
    dfheads.loc[np.logical_and(dfheads['TIME_QC_FLAG'] >= 192, dfheads['TIME_QC_FLAG'] <= 255), 'TIME_QC_FLAG'] = 0
    dfheads.loc[np.isnan(dfheads['TIME_QC_FLAG']), 'TIME_QC_FLAG'] = 9  # missing value

    # group by DATA_ID as we are creating individual profiles
    dfprofs = df.groupby('DATA_ID')
    dfheader = dfheads.groupby('DATA_ID')
    names = dfheads.columns
    for data_id in df['DATA_ID'].unique():
        data = dfprofs.get_group(data_id)
        # need to sort the data by pressure (low to high) and then parameter
        data = data.sort_values(by='PRESSURE')
        header = dfheader.get_group(data_id).reset_index()
        # check for more than one header value, skip
        if len(header) > 1:
            print('Multiple location information: ' + str(data_id))
            continue

        # the parameter names contain the variable names
        paramgroup = data.groupby('PARAMETER_CODE')

        # set up the output file name:
        outfile = os.path.join(MNF_data_path, 'NC', header['SURVEY_NAME'][0] + str(header['CAST_NO'][0])) + '.nc'

        # get the other coordinates
        lat = header['START_LAT'][0]
        lon = header['START_LON'][0]
        time = dt.datetime.strptime(header['START_TIME'][0], '%Y-%m-%d %H:%M:%S')
        botdepth = header['BOTTOM_DEPTH'][0]

        # get the coordinate/depth dimension
        press = data['PRESSURE'].unique()
        depth = -gsw.z_from_p(press, lat)

        # create a netcdf object and write depth,time,lat,long to it:
        with Dataset(outfile, 'w', format='NETCDF4') as output_netcdf_obj:
            # first create our PRES_REL dimension and variable
            output_netcdf_obj.createDimension("PRES_REL", press.size)
            output_netcdf_obj.createVariable("PRES_REL", "f", "PRES_REL")
            output_netcdf_obj['PRES_REL'][:] = press
            # and lat/lon/time vars which come from the header in the csv file:
            output_netcdf_obj.createVariable('TIME', 'd', fill_value=get_imos_parameter_info('TIME', '_FillValue'))

            output_netcdf_obj.createVariable("LATITUDE", "f8", fill_value=get_imos_parameter_info('LATITUDE', '_FillValue'))
            output_netcdf_obj.createVariable('LATITUDE_quality_control', "b", fill_value=99)
            output_netcdf_obj['LATITUDE'][:] = lat
            output_netcdf_obj['LATITUDE_quality_control'][:] = header['POSITION_QC_FLAG']
            output_netcdf_obj.createVariable("LONGITUDE", "f8",
                                             fill_value=get_imos_parameter_info('LONGITUDE', '_FillValue'))
            output_netcdf_obj['LONGITUDE'][:] = lon
            output_netcdf_obj.createVariable('LONGITUDE_quality_control', "b", fill_value=99)
            output_netcdf_obj['LONGITUDE_quality_control'][:] = header['POSITION_QC_FLAG']
            output_netcdf_obj.createVariable("BOT_DEPTH", "f8", fill_value=get_imos_parameter_info('BOT_DEPTH', '_FillValue'))
            output_netcdf_obj['BOT_DEPTH'][:] = botdepth
            # create the  DEPTH variable:
            output_netcdf_obj.createVariable('DEPTH', "f", ["PRES_REL"],
                                             fill_value=get_imos_parameter_info('DEPTH', '_FillValue'))
            output_netcdf_obj['DEPTH'][:] = depth

            # now all the other variables
            for value in data['PARAMETER_CODE'].unique():
                datf = paramgroup.get_group(value)
                dat = np.ma.masked_invalid(datf['VALUE'])
                if len(depth) != len(dat):  # check for duplicated values at each depth, skipping will mean
                    # just depth in file
                    continue
                flag = np.ma.masked_invalid(datf['QC_FLAG'])

                # check here if all flags for this parameter are missing, then no data, so skip writing it out
                if all(flag == 9):
                    print('Empty flags for ' + outfile + value)
                    # continue
                if value in vardict:
                    name = vardict[value]
                    # check here for fluorescence values > 30 which makes them a different unit
                    if 'FLU2' in name:
                        if (max(dat) > 40):
                            if (flag[dat == max(dat)][0] == 1): # good data above max for FLU2
                                name = 'FLUP'
                    # create the variable & QC variable:
                    output_netcdf_obj.createVariable(name, "f", ["PRES_REL"],
                                                     fill_value=get_imos_parameter_info(name, '_FillValue'))
                    output_netcdf_obj.createVariable(name + '_quality_control', "b", ["PRES_REL"],
                                                     fill_value=99)
                    # output the data
                    output_netcdf_obj[name][:] = dat
                    output_netcdf_obj[name + '_quality_control'][:] = flag
            # generate all the attributes for the variables & the global attributes too
            generate_netcdf_att(output_netcdf_obj, conf_file_generic, conf_file_point_of_truth=True)

            # now we can output the date/time value (need to have the generation of attributes done first)
            time_val_dateobj = date2num(time, output_netcdf_obj['TIME'].units, output_netcdf_obj['TIME'].calendar)
            output_netcdf_obj['TIME'][:] = time_val_dateobj
            output_netcdf_obj.createVariable('TIME_quality_control', "b", fill_value=99)
            output_netcdf_obj['TIME_quality_control'][:] = header['TIME_QC_FLAG']

            # global attributes from header
            for value in globdict:
                if names.str.contains(value).any():
                    var = header[value][0]
                    setattr(output_netcdf_obj, globdict[value], var)
            # do the date/time stamps individually
            setattr(output_netcdf_obj, 'date_created', dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
            setattr(output_netcdf_obj, 'date_modified', dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
            # and the datacenter
            setattr(output_netcdf_obj, 'data_centre', 'CSIRO')

if __name__ == '__main__':
    if len(sys.argv) < 1:
        raise RuntimeError("Need to include the input file path to the MNF tsv files")

    # call the converter
    convert_txt2nc(sys.argv[1])