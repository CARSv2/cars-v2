#!/usr/bin/env python
# coding: utf-8

# convert the csv file of MNF data extracted from the Data Trawler to netCDF

import pandas as pd
import datetime as dt
from pathlib import Path
import os
import sys
import gsw
import numpy as np
from netCDF4 import Dataset, date2num
from generate_netcdf_att import generate_netcdf_att, get_imos_parameter_info


def convert2nc(MNF_data_path):
    # set up dictionaries to map the cast dimensioned names to the MNF names
    imosnames = ['TEMP', 'PRES_REL', 'PSAL']
    mnfnames = ['TEMPERATURE', 'PRESSURE', 'SALINITY']
    vardict = dict(zip(mnfnames, imosnames))
    vardict2 = dict(zip(imosnames, mnfnames))
    print(vardict)
    imosglobnames = ['cruise', 'station', 'project', 'unique_code']
    mnfglobnames = ['SURVEY_NAME', 'STATION', 'PROJECT_NAME', 'MARLIN_UUID']
    globdict = dict(zip(mnfglobnames, imosglobnames))
    print(globdict)

    # FLAGS
    #
    #     Will do a flag conversion to IMOS flags, final column
    #     State        Unsigned Byte          Signed Byte         IMOS equivalent
    #     Good         0 ≤ flag ≤ 63          0 ≤ flag ≤ 63       1
    #     Suspect      64 ≤ flag ≤ 127        64 ≤ flag ≤ 127     3
    #     Bad          128 ≤ flag ≤ 191       -128 ≤ flag ≤ -65   4
    #     No QC        192 ≤ flag ≤ 255       -64 ≤ flag ≤ -1     0
    #

    # now let's try the netcdf creation
    filelist = Path(MNF_data_path).rglob('*.csv')  # read the csv file

    # each MNF file contains multiple casts
    for filn in filelist:
        # read the data:
        df = pd.read_csv(filn, error_bad_lines=False, low_memory=False)

        # the parameter names vary from file to file
        dfgroup = df.groupby(['SURVEY_NAME', 'STATION'])

        for deployment, data in dfgroup:
            # set up the output file name:
            nn = deployment[0] + str(deployment[1]).zfill(3)
            outfile = os.path.join(os.path.dirname(filn), nn) + '.nc'

            # read a file with the global attributes included and the nc configuration file
            conf_file_generic = '/generate_nc_file_attMNF'

            # get the other coordinates
            lat = data['START_LAT'].unique()
            # check for more than one lat/lon/time value, skip
            if len(lat) > 1:
                print(['Multiple location information: ' + outfile
                       ])
                continue
            lon = data['START_LON'].unique()
            time = dt.datetime.strptime(data['START_TIME'].unique().item(), '%d-%b-%Y %H:%M:%S')
            botdepth = data['BOTTOM_DEPTH'].unique()

            # get the coordinate/depth dimension
            pres = data['PRESSURE']
            depth = -gsw.z_from_p(pres, lat)

            # create a netcdf object and write depth,time,lat,long to it:
            with Dataset(outfile, 'w', format='NETCDF4') as output_netcdf_obj:
                # first create our DEPTH dimension and variable
                output_netcdf_obj.createDimension("DEPTH", depth.size)
                output_netcdf_obj.createVariable("DEPTH", "f", "DEPTH")
                output_netcdf_obj['DEPTH'][:] = depth
                # and lat/lon/time vars which come from the header in the csv file:
                output_netcdf_obj.createVariable('TIME', 'd', fill_value=get_imos_parameter_info('TIME', '_FillValue'))

                output_netcdf_obj.createVariable("LATITUDE", "f",
                                                 fill_value=get_imos_parameter_info('LATITUDE', '_FillValue'))
                output_netcdf_obj['LATITUDE'][:] = lat
                output_netcdf_obj.createVariable("LONGITUDE", "f",
                                                 fill_value=get_imos_parameter_info('LONGITUDE', '_FillValue'))
                output_netcdf_obj['LONGITUDE'][:] = lon
                output_netcdf_obj.createVariable("BOT_DEPTH", "f",
                                                 fill_value=get_imos_parameter_info('BOT_DEPTH', '_FillValue'))
                output_netcdf_obj['BOT_DEPTH'][:] = botdepth

                # now all the other variables
                for group in vardict:
                    dat = np.ma.masked_invalid(data[group])
                    if 'PRESSURE' not in group:
                        flag = np.ma.masked_invalid(data[group + '_QC'])
                    else:
                        flag = np.ma.masked_invalid(dat)
                        flag[:] = np.nan
                    # map flag values to IMOS flags
                    flag[np.logical_and(flag >= 0, flag <= 63)] = 1
                    flag[np.logical_and(flag >= 64, flag <= 127)] = 3
                    flag[np.logical_and(flag >= 128, flag <= 191)] = 4
                    flag[np.logical_and(flag >= 192, flag <= 255)] = 0
                    name = vardict[group]
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
                    var = data[value].unique().item()
                    setattr(output_netcdf_obj, globdict[value], var)
                    # do the date/time stamps individually
                setattr(output_netcdf_obj, 'date_created', dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))

if __name__ == '__main__':
    if len(sys.argv) < 1:
        raise RuntimeError("Need to include the input file path name")

    # call the converter
    convert2nc(sys.argv[1])