"""
Module to generate global attributes and variable attributes of a netcdf file
by reading a conf file.

Attributes from the conf file will be overwritten with attributes found
in imosParameters.txt for a variable if conf_file_point_of_truth is not set or
set to False

if conf_file_point_of_truth=True, any attribute in the conf file is considered
to be the point of truth

generate_netcdf_att(netcdf4_obj, conf_file)
generate_netcdf_att(netcdf4_obj, conf_file, conf_file_point_of_truth=True)

Attributes:
    netcdf4_obj: the netcdf object in write mode created by
         netCDF4.Dataset(netcdf_file_path, "w", format="NETCDF4")
    conf_file: a config text file readable by ConfigParser module

WHAT THIS DOES NOT DO :
    * This does not create dimensions, variables
    * This does not add the _FillValue attribute


Example of a conf_file:
-----------------------------------------------
[global_attributes]
abstract         = CTD Satellite
acknowledgement  = Data was sourced
author_name      = Besnard, Laurent

[TIME]
units         = days since 1950-01-01 00:00:00
standard_name = time
long_name     = analysis_time

[TIME_quality_control]
quality_control_conventions = IMOS standard flags

-----------------------------------
author: Besnard, Laurent
email : laurent.besnard@utas.edu.au
"""

import os
from configparser import ConfigParser

import numpy as np

from IMOSnetCDF import attributesFromIMOSparametersFile


def get_imos_parameter_info(nc_varname, *var_attname):
    """
    retrieves the attributes for an IMOS parameter by looking at
    imosParameters.txt
    Also can retrieve the attribute value only if specified
    if the variable or att is not found, returns []
    """

    imos_var_attr = attributesFromIMOSparametersFile()
    try:
        varname_attr = imos_var_attr[nc_varname]
    except:
        # variable not in imosParameters.txt
        return []

    # handle optional argument varatt to return the attvalue of one attname
    # only
    for att in var_attname:
        try:
            return varname_attr[att]
        except:
            return []

    return varname_attr


def _convert_num_att_type_to_var_type(nc_varname, netcdf4_obj, attval):
    var_object = netcdf4_obj[nc_varname]
    data_type  = var_object.datatype

    if data_type == 'float16':
        return np.float16(attval)
    elif data_type == 'float32':
        return np.float32(attval)
    elif data_type == 'float64':
        return np.float64(attval)
    elif data_type == 'int8':
        return np.int8(attval)
    elif data_type == 'int16':
        return np.int16(attval)
    elif data_type == 'int32':
        return np.int32(attval)
    elif data_type == 'int64':
        return np.int64(attval)

    return attval


def _find_var_conf(parser):
    """
    list NETCDF variable names from conf file
    """

    variable_list = parser.sections()
    if 'global_attributes' in variable_list:
        variable_list.remove('global_attributes')

    return variable_list


def _setup_var_att(nc_varname, netcdf4_obj, parser, conf_file_point_of_truth):
    """
    find the variable name from var_object which is equal to the category name
    of the conf file.

    parse this variable name category as a dictionnary, and creates for the
    variable object "var_object" the attributes and its corresponding values.
    This function requires the netcdf object to be already open with Dataset
    from netCDF4 module
    """

    var_object        = netcdf4_obj[nc_varname]
    var_atts          = dict(parser.items(nc_varname))  # attr from conf file
    # attr from imosParameters.txt
    varname_imos_attr = get_imos_parameter_info(nc_varname)

    # set up attributes according to conf file
    for var_attname, var_attval in var_atts.items():
        setattr(var_object, var_attname, _real_type_value(var_attval))

        # handle case when units is equal to 1 and needs to be a str
        if var_attname == 'units' and var_attval == '1':
            setattr(var_object, var_attname, str(var_attval))

    # overwrite if necessary with correct values from imosParameters.txt so this
    # file is the point of truth . see conf_file_point_of_truth variable

    def _set_imos_var_att_if_exist(attname):
        try:
            if varname_imos_attr[attname] != [] and varname_imos_attr[attname] != '':
                attval = varname_imos_attr[attname]
                if attname == 'valid_min' or attname == 'valid_max':
                    attval = _convert_num_att_type_to_var_type(nc_varname, netcdf4_obj, attval)

                if not conf_file_point_of_truth:
                    var_object.__setattr__(attname, attval)
                else:
                    # if conf file point of truth and attribute does already
                    # exist in netcdf file, then we add the default attribute
                    if not hasattr(var_object, attname):
                        var_object.__setattr__(attname, attval)
        except:
            pass

    if varname_imos_attr:
        _set_imos_var_att_if_exist('standard_name')
        _set_imos_var_att_if_exist('long_name')
        _set_imos_var_att_if_exist('units')
        _set_imos_var_att_if_exist('valid_min')
        _set_imos_var_att_if_exist('valid_max')

    if 'quality_control_conventions' in list(var_atts.keys()):
        # IMOS QC only . IMOS convention 1.3 and 1.4
        if var_atts['quality_control_conventions'] == 'IMOS standard flags' or var_atts['quality_control_conventions'] == 'IMOS standard set using the IODE flags':
            var_object.__setattr__('valid_min', np.byte(0))
            var_object.__setattr__('valid_max', np.byte(9))
            var_object.__setattr__('flag_values', np.byte(list(range(0, 10))))
            var_object.__setattr__('flag_meanings', 'No_QC_performed Good_data Probably_good_data Bad_data_that_are_potentially_correctable Bad_data Value_changed Not_used Not_used Not_used Missing_value')


def _setup_gatts(netcdf_object, parser):
    """
    read the "global_attributes" from gatts.conf and create the global
    attributes from an already opened netcdf_object
    """
    if not ConfigParser.has_section(parser, 'global_attributes'):
        return

    gatts = dict(parser.items('global_attributes'))
    for gattname, gattval in gatts.items():
        try:
            setattr(netcdf_object, gattname, _real_type_value(gattval))
        except:
            # handle unicode values such as @
            netcdf_object.__setattr__(gattname, str(gattval))


def _call_parser(conf_file):
    parser = ConfigParser()
    parser.optionxform = str  # to preserve case
    parser.read(conf_file)
    return parser


def _real_type_value(s):
    try:
        return int(s)
    except:
        pass

    try:
        return float(s)
    except:
        pass

    return string_escape(str(s), encoding='utf-8')


def string_escape(s, encoding='utf-8'):
    """https://stackoverflow.com/questions/14820429/how-do-i-decodestring-escape-in-python3"""
    return (s.encode('latin1')         # To bytes, required by 'unicode-escape'
             .decode('unicode-escape') # Perform the actual octal-escaping decode
             .encode('latin1')         # 1:1 mapping back to bytes
             .decode(encoding))        # Decode original encoding


def generate_netcdf_att(netcdf4_obj, conf_file, conf_file_point_of_truth=False):
    """
    main function to generate the attributes of a netCDF file
    """
    if not isinstance(netcdf4_obj, object):
        raise ValueError('%s is not a netCDF4 object' % netcdf4_obj)

    if not os.path.exists(conf_file):
        raise ValueError('%s file does not exist' % conf_file)

    parser = _call_parser(conf_file)
    _setup_gatts(netcdf4_obj, parser)

    variable_list = _find_var_conf(parser)
    for var in variable_list:
        # only create attributes for variable which already exist
        if var in list(netcdf4_obj.variables.keys()):
            _setup_var_att(var, netcdf4_obj, parser, conf_file_point_of_truth)
