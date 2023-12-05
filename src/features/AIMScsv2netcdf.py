#!/usr/bin/env python
# coding: utf-8

# Let's use the netcdf tools and known method to create the netcdf format I want. seems that xarray is peculiar to
# gridded data and treats time very specifically and I can't get past it needing to add a dimension to time and use
# it as a coordinate.

import pandas as pd
import datetime as dt
from pathlib import Path
import os, sys
import numpy as np
from netCDF4 import Dataset, date2num
from generate_netcdf_att import generate_netcdf_att, get_imos_parameter_info

def convert2nc(AIMS_data_path):
    # set up dictionaries to map the cast dimensioned names to the aims names
    # Have ignored all other parameters for now except for PSAL, TEMP, PRES_REL, DEPTH. The other ones have mixed units and
    # haven't the time to parse the units appropriately.
    imosnames = ['LATITUDE', 'LONGITUDE', 'TIME', 'BOT_DEPTH', 'TEMP', 'PRES_REL', 'PSAL']
    aimsnames = ['LATITUDE', 'LONGITUDE', 'SAMPLE DATE', 'TO DEPTH', 'Temp', 'Pres', 'Salinity']
    vardict = dict(zip(aimsnames, imosnames))
    vardict2 = dict(zip(imosnames, aimsnames))
    print(vardict2)
    imosglobnames = ['cruise', 'disclaimer', 'attribution', 'license']
    aimsglobnames = ['STATION NAME', 'DISCLAIMER', 'ATTRIBUTION', 'COPYRIGHT']
    globdict = dict(zip(aimsglobnames, imosglobnames))
    print(globdict)

    # now let's read in the csv CTD data from AIMS

    filelist = Path(AIMS_data_path).rglob('*.csv')  # read the csv file
    for filn in filelist:

        # set up the output file name:
        nn = os.path.splitext(os.path.basename(filn))
        outfile = os.path.join(os.path.dirname(filn), 'NC2', nn[0]) + '.nc'

        # read the data:
        df = pd.read_csv(filn, skiprows=15)

        # header information
        dfhead = pd.read_csv(filn, skiprows=range(15, 9999))
        # if no time field, continue - there are a few without any date/time information
        if not dfhead[names[0]].str.contains(vardict2['TIME']).any():
            continue

        # the parameter names vary from file to file
        dfgroup = df.groupby('PARAMETER')

        # read a file with the global attributes included and the nc configuration file
        conf_file_generic = '/tube1/cow074/Documents/cars-v2/notebooks/generate_nc_file_att'
        # get the data from the header
        dfhead = pd.read_csv(filn, skiprows=range(15, 9999))
        names = dfhead.columns

        # get the coordinate/depth dimension
        # depth = df.loc[df['PARAMETER'].str.contains('Depth'), 'VALUE']
        depth = df['DEPTH'].unique()
        # get the other coordinates
        lat = dfhead.loc[dfhead[names[0]].str.contains(vardict2['LATITUDE']), names[1]].item()
        lon = dfhead.loc[dfhead[names[0]].str.contains(vardict2['LONGITUDE']), names[1]].item()
        time = dt.datetime.strptime(dfhead.loc[dfhead[names[0]].str.contains(vardict2['TIME']), names[1]].item(),
                                    '%d-%m-%Y')

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

            # now all the other variables
            for group in df['PARAMETER'].unique():
                data = np.ma.masked_invalid(dfgroup.get_group(group)['VALUE'])
                if len(depth) != len(data):  # some aims files have duplicated values at each depth, skipping will mean
                    # just depth in file
                    continue
                flag = np.ma.masked_invalid(dfgroup.get_group(group)['QAQC_FLAG'])
                for value in vardict:
                    if value in group:
                        name = vardict[value]
                        # create the variable & QC variable:
                        output_netcdf_obj.createVariable(name, "f", ["DEPTH"],
                                                         fill_value=get_imos_parameter_info(name, '_FillValue'))
                        output_netcdf_obj.createVariable(name + '_quality_control', "b", ["DEPTH"],
                                                         fill_value=99)

                        # output the data
                        output_netcdf_obj[name][:] = data
                        output_netcdf_obj[name + '_quality_control'][:] = flag
            # generate all the attributes for the variables & the global attributes too
            generate_netcdf_att(output_netcdf_obj, conf_file_generic, conf_file_point_of_truth=True)

            # now we can output the date/time value (need to have the generation of attributes done first)
            time_val_dateobj = date2num(time, output_netcdf_obj['TIME'].units, output_netcdf_obj['TIME'].calendar)
            output_netcdf_obj['TIME'][:] = time_val_dateobj

            # global attributes from header
            for value in globdict:
                if dfhead[names[0]].str.contains(value).any():
                    var = dfhead.loc[dfhead[names[0]].str.contains(value), names[1]].item()
                    setattr(output_netcdf_obj, globdict[value], var)
                    # do the date/time stamps individually
            datt = dt.datetime.strptime(dfhead.loc[dfhead[names[0]].str.contains('FILE CREATED'), names[1]].item(),
                                        '%d-%m-%Y')
            setattr(output_netcdf_obj, 'date_created', datt.strftime("%Y-%m-%dT%H:%M:%SZ"))
            setattr(output_netcdf_obj, 'date_modified', dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))

if __name__ == '__main__':
    if len(sys.argv) < 1:
        raise RuntimeError("Need to include the input file path to the AIMS csv files")

    # call the converter
    convert2nc(sys.argv[1])