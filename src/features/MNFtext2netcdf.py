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
    imosnames = ['TEMP', 'PRES_REL', 'PSAL', 'DOXY']
    mnfnames = ['TEMPERATURE', 'PRESSURE', 'SALINITY', 'OXYGEN']
    vardict = dict(zip(mnfnames, imosnames))
    vardict2 = dict(zip(imosnames, mnfnames))
    print(vardict)
    imosglobnames = ['cruise', 'station', 'project', 'site_code', 'unique_code']
    mnfglobnames = ['SURVEY_NAME', 'CAST_NO', 'SURVEY_NAME', 'MARLIN_ID', 'MARLIN_UUID']
    globdict = dict(zip(mnfglobnames, imosglobnames))
    print(globdict)

    # read a file with the global attributes included and the nc configuration file
    conf_file_generic = '/tube1/cow074/Documents/cars-v2/src/features/IMOScode/generate_nc_file_att'

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
            # first create our DEPTH dimension and variable
            output_netcdf_obj.createDimension("DEPTH", depth.size)
            output_netcdf_obj.createVariable("DEPTH", "f", "DEPTH")
            output_netcdf_obj['DEPTH'][:] = depth
            # and lat/lon/time vars which come from the header in the csv file:
            output_netcdf_obj.createVariable('TIME', 'd', fill_value=get_imos_parameter_info('TIME', '_FillValue'))

            output_netcdf_obj.createVariable("LATITUDE", "f8", fill_value=get_imos_parameter_info('LATITUDE', '_FillValue'))
            output_netcdf_obj['LATITUDE'][:] = lat
            output_netcdf_obj.createVariable("LONGITUDE", "f8",
                                             fill_value=get_imos_parameter_info('LONGITUDE', '_FillValue'))
            output_netcdf_obj['LONGITUDE'][:] = lon
            output_netcdf_obj.createVariable("BOT_DEPTH", "f8", fill_value=get_imos_parameter_info('BOT_DEPTH', '_FillValue'))
            output_netcdf_obj['BOT_DEPTH'][:] = botdepth

            # now all the other variables
            for value in data['PARAMETER_CODE'].unique():
                datf = paramgroup.get_group(value)
                dat = np.ma.masked_invalid(datf['VALUE'])
                if len(depth) != len(dat):  # check for duplicated values at each depth, skipping will mean
                    # just depth in file
                    continue
                flag = np.ma.masked_invalid(datf['QC_FLAG'])
                # map flag values to IMOS flags
                flag[np.logical_and(flag >= 0, flag <= 63)] = 1
                flag[np.logical_and(flag >= 64, flag <= 127)] = 3
                flag[np.logical_and(flag >= 128, flag <= 191)] = 4
                flag[np.logical_and(flag >= 192, flag <= 255)] = 0

                if value in vardict:
                    name = vardict[value]
                    # create the variable & QC variable:
                    output_netcdf_obj.createVariable(name, "f", ["DEPTH"],
                                                     fill_value=get_imos_parameter_info(name, '_FillValue'))
                    output_netcdf_obj.createVariable(name + '_quality_control', "b", ["DEPTH"],
                                                     fill_value=99)
                    # output the data
                    output_netcdf_obj[name][:] = dat
                    output_netcdf_obj[name + '_quality_control'][:] = flag
            # generate all the attributes for the variables & the global attributes too
            generate_netcdf_att(output_netcdf_obj, conf_file_generic, conf_file_point_of_truth=True)

            # now we can output the date/time value (need to have the generation of attributes done first)
            time_val_dateobj = date2num(time, output_netcdf_obj['TIME'].units, output_netcdf_obj['TIME'].calendar)
            output_netcdf_obj['TIME'][:] = time_val_dateobj

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