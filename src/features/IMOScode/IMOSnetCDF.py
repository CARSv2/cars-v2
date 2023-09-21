#! /usr/bin/env python3
#
# Python module to manage IMOS-standard netCDF data files.


import csv
import os
import re
import sys
import time
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timedelta
from shutil import move
from tempfile import mkstemp

import numpy as np
from netCDF4 import Dataset

#############################################################################

# File containing default attributes that apply to all netCDF files (loaded later).
SCRIPT_DIR         = os.path.dirname(os.path.realpath(__file__))
baseAttributesFile = os.path.join(SCRIPT_DIR, 'IMOSbase.attr')
imosParametersFile = os.path.join(SCRIPT_DIR, 'imosParameters.txt')
defaultAttributes  = {}

# Epoch for time variabe
epoch = datetime(1950,1,1)

# Set this to True for extra debugging output and not deleting empty attributes
DEBUG = False


#############################################################################

class IMOSnetCDFFile(object):
    """
    netCDF file following the IMOS netCDF conventions.

    Based on the IMOS NetCDF User Manual (v1.3) and File Naming
    Convention (v1.3), which can be obtained from
    http://imos.org.au/facility_manuals.html

    Using the netcdf4-python module for file access.
    """

    def __init__(self, filename='', attribFile=None):
        """
        Create a new empty file, pre-filling some mandatory global
        attributes.  If filename is not given, a temporary file is
        opened, which can be renamed after closing.
        Optionally a file listing global and variable attributes can be given.
        """

        # Create temporary filename if needed
        if filename=='':
            fd, filename = mkstemp(suffix='.nc')
            self.__dict__['tmpFile'] = filename

        # Open the file and create dimension and variable lists
        self.__dict__['filename'] = filename
        self.__dict__['_F'] = Dataset(filename, 'w', format='NETCDF3_CLASSIC')
        if attribFile:
            self.__dict__['attributes'] = attributesFromFile(attribFile, defaultAttributes)
        else:
            self.__dict__['attributes'] = deepcopy(defaultAttributes)

        # Create mandatory global attributes
        if '' in self.attributes:
            self.setAttributes(self.attributes[''])


    def __str__(self):
        "String representation of file."
        return self._F.__str__()


    def __getattr__(self, name):
        "Return the value of a global attribute."
        try:
            exec('attr = self._F.' + name)
        except AttributeError:
            attr = self.__dict__[name]
        return attr


    def __setattr__(self, name, value):
        "Set a global attribute."
        exec('self._F.' + name + ' = value')


    def __delattr__(self, name):
        "Delete a global attribute"
        exec('del self._F.' + name)


    def close(self):
        """
        Update global attributes, write all data to the file and close.
        Rename the file if a temporary file was used.
        """
        self.updateAttributes()
        self.date_created = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        if not DEBUG: self.deleteEmptyAttributes()
        self._F.close()
        if 'tmpFile' in self.__dict__:
            # rename to desired filename and set permissions
            move(self.tmpFile, self.filename)
            os.chmod(self.filename, 0o644)
        if DEBUG:
            print('IMOSnetCDF: wrote ' + self.filename, file=sys.stderr)


    def createDimension(self, name, length=None):
        "Create a new dimension."
        self._F.createDimension(name, length)


    def createVariable(self, name, dtype, dimensions, fill_value=None):
        """
        Create a new variable in the file.
        Returns an IMOSNetCDFVariable object.
        """

        if name in self.attributes:
            # if fill_value not given, use default
            if fill_value is None:
                fill_value = self.attributes[name].pop('_FillValue', None)

            # override data type with default for variable, if default exists
            dtype = self.attributes[name].pop('__data_type', dtype)

        newvar = IMOSnetCDFVariable( self._F.createVariable(name, dtype, dimensions,
                                                            fill_value=fill_value) )
        self.variables[name] = newvar

        # add attributes
        if name in self.attributes:
            newvar.setAttributes(self.attributes[name])

        return newvar


    def sync(self):
        "Update global attributes and write all buffered data to the disk file."
        self.updateAttributes()
        self._F.sync()

    flush = sync


    def getAttributes(self):
        "Return the global attributes of the file as a dictionary."
        return self._F.__dict__


    def setAttributes(self, aDict, **attr):
        """
        Set global attributes from an OrderedDict mapping attribute
        names to values.  Any additional keyword arguments are also
        added as attributes (order not preserved).
        """
        self._F.setncatts(aDict)
        self._F.setncatts(attr)


    def updateAttributes(self):
        """
        Based on the dimensions and variables that have been set,
        update global attributes such as geospatial_min/max and
        time_coverage_start/end.
        """

        # TIME
        if 'TIME' in self.variables:
            time = self.variables['TIME']
            self.time_coverage_start = (epoch + timedelta(time[:].min())).isoformat() + 'Z'
            self.time_coverage_end   = (epoch + timedelta(time[:].max())).isoformat() + 'Z'

        # LATITUDE
        if 'LATITUDE' in self.variables:
            lat = self.variables['LATITUDE']
            self.geospatial_lat_min = lat[:].min()
            self.geospatial_lat_max = lat[:].max()

        # LONGITUDE
        if 'LONGITUDE' in self.variables:
            lon = self.variables['LONGITUDE']
            self.geospatial_lon_min = lon[:].min()
            self.geospatial_lon_max = lon[:].max()


    def deleteEmptyAttributes(self):
        "Delete all global and variable attributes that have an empty string value."

        # global attributes
        for k, v in list(self.getAttributes().items()):
            if v == '':  self.__delattr__(k)

        # variable attributes
        for var in list(self.variables.values()):
            for k, v in list(var.getAttributes().items()):
                if v == '':  var.__delattr__(k)


    def setDimension(self, name, values, fill_value=None):
        """
        Create a dimension with the given name and values, and return
        the corresponding IMOSnetCDFVariable object.
        """
        self.createDimension(name, np.size(values))
        return self.setVariable(name, values, (name,), fill_value)


    def setVariable(self, name, values, dimensions, fill_value=None):
        """
        Create a variable with the given name, values and dimensions,
        and return the corresponding IMOSnetCDFVariable object.
        """

        # make sure input values are in an numpy array (even if only one value)
        varray = np.array(values)

        ### should add check that values has the right shape for dimensions !!

        # create the variable
        var = self.createVariable(name, varray.dtype, dimensions, fill_value)

        # add the values
        varray.resize(var.shape)
        var[:] = varray

        return var


    def standardFileName(self, datacode='', product='', path='', rename=True):
        """
        Create an IMOS-standard (v1.3) name for the file based on the
        current attributes and variables in the file and return as a
        string. updateAttributes() should be run first.

        If path is given, it is added to the beginning of the file name.

        If rename is True, the file will be renamed to the standard name upon close().
        """

        globalattr = self.getAttributes()

        name = 'IMOS'

        # facility code
        assert 'institution' in globalattr, 'standardFileName: institution attribute not set!'
        name += '_' + self.institution

        # data code
        if datacode:
            name += '_' + datacode

        # start date
        assert 'time_coverage_start' in globalattr, 'standardFileName: time_coverage_start not set!'
        name += '_' + re.sub('[-:]', '', self.time_coverage_start)

        # site code
        assert 'site_code' in globalattr, 'standardFileName: site_code not set!'
        name += '_' + self.site_code

        # file version
        assert 'file_version' in globalattr, 'standardFileName: file_version not set!'
        m = re.findall('^Level ([0-3])', self.file_version)
        if not m:
            print('Could not extract FV number from file_version attribute! Assuming 0.', file=sys.stderr)
            m = ['0']
        name += '_FV0'+m[0]

        # product type
        if product:
            name += '_'+product

        # end date
        assert 'time_coverage_end' in globalattr, 'standardFileName: time_coverage_end not set!'
        name += '_END-' + re.sub('[-:]', '', self.time_coverage_end)

        # creation date
        now = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
        name += '_C-' + now

        # extension
        name += '.nc'

        if path:
            name = os.path.join(path, name)

        if rename:
            self.__dict__['filename'] = name

        return name



#############################################################################

class IMOSnetCDFVariable(object):
    """
    Variable in an IMOS netCDF file.

    This is just a wrapper for the Scientific.IO.NetCDF.NetCDFVariable
    class and has similar functionality. Variable attributes can also
    be accessed via the getAttributes() and setAttributes() methods.
    """

    def __init__(self, ncvar):
        """
        Creates a new object to represent the given NetCDFVariable.
        For internal use by IMOSnetCDFFile methods only.
        """
        self.__dict__['_V'] = ncvar


    def __str__(self):
        "String representation of variable."
        return self._V.__str__()


    def __getattr__(self, name):
        "Return the value of a variable attribute."
        exec('attr = self._V.' + name)
        return attr


    def __setattr__(self, name, value):
        """
        Set an attribute of the variable.
        Values of _FillValue, valid_min, and valid_max are automatically
        cast to the type of the variable.
        """
        if name in ('_FillValue', 'valid_min', 'valid_max') and value != "":
            exec('self._V.' + name + ' = np.array([value], dtype=self.dtype)')
        else:
            exec('self._V.' + name + ' = value')


    def __delattr__(self, name):
        "Delete a variable attribute"
        exec('del self._V.'+name)


    def __getitem__(self, key):
        "Return (any slice of) the variable values."
        return self._V[key]


    def __setitem__(self, key, value):
        "Set (any slice of) the variable values."
        self._V[key] = value


    def getAttributes(self):
        "Return the attributes of the variable."
        return self._V.__dict__


    def setAttributes(self, aDict, **attr):
        """
        Set variable attributes from an OrderedDict mapping attribute
        names to values.  Any additional keyword arguments are also
        added as attributes (order not preserved).
        """

        # Note: can't use self._V.setncatts() because that skips the
        # special type-setting functionality we added in
        # self.__setattr__
        if aDict:
            for name, value in aDict.items():
                self.__setattr__(name, value)
        if attr:
            for name, value in attr.items():
                self.__setattr__(name, value)


    def getValue(self):
        "Return the value of a scalar variable."
        return self._V.getValue()


    def setValue(self, value):
        "Assign a scalar value to the variable."
        self._V.assignValue(value)

    def typecode(self):
        "Returns the variable's type code (single character)."
        return self.dtype.char




#############################################################################


def attributeValueFromString(string):
    """
    Convert a string into an integer of float, if possible, otherwise
    keep it as a string but strip any leading or trailing white space
    and quotes.
    """
    try:
        return int(string)
    except:
        try:
            return float(string)
        except:
            return string.strip(' "\'')


def attributesFromFile(filename, inAttr={}):
    """
    Reads a list of netCDF attribute definitions from a file into a
    dictionary. The keys are variable names (or '' for global
    attributes) and each value is an OrderedDict object mapping
    attribute names to values.

    These OrderedDict objects can then be used to set attributes in
    IMOSnetCDF and IMOSnetCDFVariable objects.

    If an existing dict is passed as a second argument, attributes are
    appended to a copy of it, with newer values overriding anything previously
    set for a given attribute. (The input dict is not modified.)
    """

    import re

    F = open(filename)
    # parse lines in the form 'VARIABLE:attribute_name = value'
    lines = re.findall('^\s*(\w*):(\S+)\s*=\s*(.+)', F.read(), re.M)
    F.close()

    attr = deepcopy(inAttr)
    for (var, aName, aVal) in lines:

        if var not in attr:
            attr[var] = OrderedDict()

        attr[var][aName] = attributeValueFromString(aVal.rstrip(';'))

    return attr


def attributesFromIMOSparametersFile(inAttr={}):
    """
    Reads in the default variable attributes from the
    imosParameters.txt file in the IMOS Matlab Toolbox.

    Columns in the file are:
    0) parameter name,
    1) is cf parameter,
    2) standard/long name,
    3) units of measurement,
    4) data code,
    5) fillValue,
    6) validMin,
    7) validMax,
    8) NetCDF 3.6.0 type

    As for attributesFromFile, attributes are added to a copy of a
    dict given as an optional input argument.
    """

    nCol = 9

    with open(imosParametersFile) as F:
        rd = csv.reader(F, skipinitialspace=True)

        attr = deepcopy(inAttr)
        for line in rd:
            if len(line) < nCol or line[0][0] == '%': continue

            var = line[0]
            if var not in attr:
                attr[var] = OrderedDict()

            if int(line[1]):
                attr[var]['standard_name'] = line[2].strip(' "\'')

            attr[var]['long_name'] = line[2].strip(' "\'')

            attr[var]['units'] = line[3].strip(' "\'').replace('percent','%')

            attr[var]['_FillValue'] = attributeValueFromString(line[5])

            attr[var]['valid_min'] = attributeValueFromString(line[6])

            attr[var]['valid_max'] = attributeValueFromString(line[7])

            dtype = line[8].strip(' "\'')
            if dtype == 'float':
                attr[var]['__data_type'] = 'f'
            elif dtype == 'double':
                attr[var]['__data_type'] = 'd'
            elif dtype == 'char':
                attr[var]['__data_type'] = 'c'
            elif dtype == 'int':
                attr[var]['__data_type'] = 'i'
            elif dtype == 'byte':
                attr[var]['__data_type'] = 'b'
            else:
                print('Unknown data type in %s: %s' % (imosParametersFile, dtype), file=sys.stderr)

            # attr[var]['__data_code'] = attributeValueFromString(line[4])

    return attr




#############################################################################

# now load the default IMOS attributes
parameterAttributes = attributesFromIMOSparametersFile()
defaultAttributes = attributesFromFile(baseAttributesFile, parameterAttributes)
