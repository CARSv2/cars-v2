import numpy as np
import xarray
import matplotlib.pyplot as plt
import pandas as pd
import os
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import gsw as TEOS_10
import colorcet as cc
import matplotlib.gridspec as gridspec
import cmocean 

interp_levels = np.arange(0,6001,10)
START_YEAR = 1988
END_YEAR   = 1990

CORA_VERSION = 50
VARIABLE     = 'salinity'
PLATFORM     = ['CTD']

output_file_path = '/OSM/CBR/OA_DCFP/work/cha674/CORA_interrogation/Figures/'

file_path = '/OSM/CBR/OA_DCFP/work/cha674/CORA_interrogation/Stat_files_v' + str(CORA_VERSION) + '/'
file_name_pre  = 'CORA_v' + str(CORA_VERSION) + '_' + VARIABLE + '_'

n_points_on_level = []
time              = []
lon               = []
lat               = []
max_depth         = []


for i_platform in range(0,len(PLATFORM)):
    file_name_post = '_stats_' + PLATFORM[i_platform] + 'QC012.npz'

    for i_year in range(START_YEAR,END_YEAR):
        complete_file_name = file_name_pre + str(i_year) + file_name_post
        print('Opening file: ', complete_file_name)
        file_obj            = np.load(file_path+complete_file_name)
        if i_year == START_YEAR:
        
            n_points_on_level_tmp   = file_obj['n_points_on_level']        
            time_tmp                = file_obj['unique_dates']

            lon_tmp                 = file_obj['longitude']
            lat_tmp                 = file_obj['latitude']
            max_depth_tmp           = file_obj['max_depth']

        else:
            n_points_on_level_tmp = np.concatenate([n_points_on_level_tmp,file_obj['n_points_on_level']])
            time_tmp              = np.concatenate([time_tmp,file_obj['unique_dates']])

            lon_tmp               = np.concatenate([lon_tmp,file_obj['longitude']])
            lat_tmp               = np.concatenate([lat_tmp,file_obj['latitude']])
            max_depth_tmp         = np.concatenate([max_depth_tmp,file_obj['max_depth']])

    n_points_on_level.append(n_points_on_level_tmp)
    time.append(time_tmp)
    lon.append(lon_tmp)
    lat.append(lat_tmp)
    max_depth.append(max_depth_tmp)



fig = plt.figure(0,figsize=(30,20))
gs = gridspec.GridSpec(len(PLATFORM), 2, width_ratios=[20,1])

for i_platform in range(0,len(PLATFORM)):

    ax = fig.add_subplot(gs[i_platform,0])
    cs=ax.contourf(time[i_platform],-interp_levels,n_points_on_level[i_platform].T,np.arange(0,51,10),cmap=cc.cm.rainbow,extend='both')
    ax.set_ylabel('Depth (m)',fontsize='15')
    ax.grid(True)
    ax.annotate(PLATFORM[i_platform],
            xy=(-0.1, 1.05), xycoords='axes fraction',
            horizontalalignment='left', verticalalignment='bottom',fontsize=15,color='black')

    ax.set_ylabel('Depth (m)',fontsize='15')
    if i_platform != len(PLATFORM)-1:
        
        ax.set_xticklabels([])
     
#ax = fig.add_subplot(gs[1,0])
#cs=ax.contourf(time,-interp_levels,n_points_on_level.T,np.arange(0,100.1,20),cmap=cc.cm.rainbow,extend='both')

#ax.grid(True)

ax = fig.add_subplot(gs[0,0])
ax.annotate('Version: ' + str(CORA_VERSION/10.0),
            xy=(-0.1, 1.2), xycoords='axes fraction',
            horizontalalignment='left',
            verticalalignment='bottom',fontsize=20,color='black')
#ax.annotate('(b) XBT',
#            xy=(-0.1, 1.05), xycoords='axes fraction',
#            horizontalalignment='left', verticalalignment='bottom',fontsize=15,color='black')



ax = fig.add_subplot(gs[len(PLATFORM)-1,0])
ax.set_xlabel('Date',fontsize='15')
cbar_axes = fig.add_subplot(gs[:,1])
cbar = fig.colorbar(cs,cax=cbar_axes)
cbar.set_label(r'# Obs. per day',fontsize=20)

output_file_name = 'v' + str(CORA_VERSION) + '_Npoints_on_levels_' + VARIABLE + '_' + str(START_YEAR) + '_' + str(END_YEAR-1)
plt.savefig(output_file_path + output_file_name + '.pdf', dpi=200)
plt.savefig(output_file_path + output_file_name + '.png', dpi=200)
plt.savefig(output_file_path + output_file_name + '.eps', dpi=200)
#print(time)
lon_grid = np.arange(-180,180,1)
lat_grid = np.arange(-90,90,1)


land = cfeature.NaturalEarthFeature(category='physical', name='land', scale='50m',
                                        facecolor='grey')
states = cfeature.NaturalEarthFeature(category='cultural', scale='50m', facecolor='none',
                                      name='admin_1_states_provinces_shp')

fig = plt.figure(1,figsize=(30,20))
gs = gridspec.GridSpec(len(PLATFORM), 2, width_ratios=[20,1])
for i_platform in range(0,len(PLATFORM)):


    points_hist, xedges, yedges = np.histogram2d(lon[i_platform], lat[i_platform], bins=(lon_grid, lat_grid))
    points_hist[points_hist==0] = np.nan
    points_hist = points_hist/float(END_YEAR-START_YEAR)
    ax  = fig.add_subplot(gs[i_platform,0],projection=ccrs.Mollweide())
    cs =ax.pcolormesh(xedges[1::],yedges[1::],points_hist.T,vmin=1,vmax=30,cmap=cc.cm.rainbow,transform=ccrs.PlateCarree())
    ax.coastlines()
    ax.set_global()
    ax.add_feature(land)
    ax.gridlines()

    ax.annotate(PLATFORM[i_platform],
            xy=(-0.1, 1.05), xycoords='axes fraction',
            horizontalalignment='left', verticalalignment='bottom',fontsize=15,color='black')




ax  = fig.add_subplot(gs[0,0],projection=ccrs.Mollweide())
ax.annotate('Version: ' + str(CORA_VERSION/10.0),
            xy=(-0.40, 1.25), xycoords='axes fraction',
            horizontalalignment='left',
            verticalalignment='bottom',fontsize=20,color='black')
ax.annotate('Years: ' +  str(START_YEAR) + '-' + str(END_YEAR-1),
            xy=(-0.40, 1.15), xycoords='axes fraction',
            horizontalalignment='left',
            verticalalignment='bottom',fontsize=20,color='black')


cbar_axes = fig.add_subplot(gs[:,1])
cbar = fig.colorbar(cs,cax=cbar_axes)
cbar.set_label(r'# Obs. per year',fontsize=20)

output_file_name = 'v' + str(CORA_VERSION) + '_Global_histogram_' + VARIABLE + '_' + str(START_YEAR) + '_' + str(END_YEAR-1)
plt.savefig(output_file_path + output_file_name + '.pdf', dpi=200)
plt.savefig(output_file_path + output_file_name + '.png', dpi=200)
plt.savefig(output_file_path + output_file_name + '.eps', dpi=200)




depth_range = [[0,1000],[1000,2000],[2000,4000],[4000,6000]]
n_ranges = len(depth_range)

fig = plt.figure(2,figsize=(30,20))
gs = gridspec.GridSpec(n_ranges, len(PLATFORM)+1, width_ratios=[20,1])
for i_platform in range(0,len(PLATFORM)):
    counter = 0

    for i_depth_range in depth_range:
   
        ax = fig.add_subplot(gs[counter,i_platform],projection=ccrs.Mollweide())
        if counter==0:
            ax.annotate(PLATFORM[i_platform],
                xy=(0.45, 1.1), xycoords='axes fraction',
                horizontalalignment='left',
                verticalalignment='bottom',fontsize=20,color='black')
        print(i_depth_range)

#    ax  = fig.add_subplot(n_ranges,2,counter,projection=ccrs.Mollweide())
        idx_depth = np.nonzero(np.logical_and(max_depth[i_platform]>i_depth_range[0],max_depth[i_platform]<=i_depth_range[1]))[0]

        lon_depth_range = lon[i_platform][idx_depth]
        lat_depth_range = lat[i_platform][idx_depth]
        depth_depth_range = max_depth[i_platform][idx_depth]

        if len(lat_depth_range)!=0:
            cs = ax.scatter(lon_depth_range,lat_depth_range,c=depth_depth_range,s=20,transform=ccrs.PlateCarree(),vmin=0,vmax=6000,cmap=cmocean.cm.deep)
        ax.coastlines()
        ax.set_global()

        ax.add_feature(land)
#    ax.add_feature(cfeature.OCEAN)
        ax.gridlines()
 
        ax.annotate(str(depth_range[counter][0]) + '-' + str(depth_range[counter][1]) + ' m',
            xy=(-0.1, 1.05), xycoords='axes fraction',
            horizontalalignment='left', verticalalignment='bottom',fontsize=15,color='black')

        counter=counter+1


#fig.colorbar(cs,ax=ax)
cbar_axes = fig.add_subplot(gs[:,len(PLATFORM)])
cbar = fig.colorbar(cs,cax=cbar_axes)
cbar.set_label(r'Depth (m)',fontsize=20)

ax = fig.add_subplot(gs[0,0],projection=ccrs.Mollweide())

ax.annotate('Version: ' + str(CORA_VERSION/10.0),
            xy=(-0.40, 1.5), xycoords='axes fraction',
            horizontalalignment='left',
            verticalalignment='bottom',fontsize=20,color='black')

ax.annotate('Years: ' +  str(START_YEAR) + '-' + str(END_YEAR-1),
            xy=(-0.40, 1.3), xycoords='axes fraction',
            horizontalalignment='left',
            verticalalignment='bottom',fontsize=20,color='black')

output_file_name = 'v' + str(CORA_VERSION) + '_Global_obs_locs_sort_depth_XBT_CTD_' + VARIABLE + '_' + str(START_YEAR) + '_' + str(END_YEAR-1)
plt.savefig(output_file_path + output_file_name + '.pdf', dpi=200)
plt.savefig(output_file_path + output_file_name + '.png', dpi=200)
plt.savefig(output_file_path + output_file_name + '.eps', dpi=200)
plt.show()

