import datetime as dt
from pathlib import Path
import os
import gsw
import numpy as np
from netCDF4 import Dataset, date2num
from generate_netcdf_att import generate_netcdf_att, get_imos_parameter_info


def convert_txt2nc(MNF_data_path):
    # set up dictionaries to map the cast dimensioned names to the MNF names
    imosnames = ['TEMP', 'PRES_REL', 'PSAL']
    mnfnames = ['TEMPERATURE', 'PRESSURE', 'SALINITY']
    vardict = dict(zip(mnfnames, imosnames))
    vardict2 = dict(zip(imosnames, mnfnames))
    print(vardict)
    imosglobnames = ['cruise', 'station', 'project', 'site_code', 'unique_code']
    mnfglobnames = ['SURVEY_NAME', 'STATION', 'PROJECT_NAME', 'MARLIN_ID', 'MARLIN_UUID']
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
    filelist = Path(MNF_data_path).rglob('*.tsv')  # read the tsv file extracted from the Oracle database

    # two files, one is the station information ('ctd_header.tsv') other is the data ('ctd_data.tsv')

    # link is the data_id field
