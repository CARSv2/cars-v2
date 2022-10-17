import numpy as np
import xarray
import matplotlib.pyplot as plt
import pandas as pd
import os
import cartopy.crs as ccrs
import gsw as TEOS_10


file_name_stem = 'CO_DMQCGL01_'
data_type_dict = {'XBT': ['PR_XB','PR_BA','PR_TE','PR_OC','PR_SH','PR_GL'],
                  'CTD': ['PR_OC','PR_TE','PR_BA','PR_CT','PR_IC','PR_ME','PR_SD','PR_OS','PR_SH'],
                  'Seal': ['PR_OC','PR_TE','PR_BA','PR_CT','PR_IC','PR_ME','PR_SD','PR_OS'],
                  'Float': ['PR_PF','PR_TE'],
                  'All' : ['PR_PF','PR_XB','PR_BA','PR_TE','PR_OC','PR_SH','PR_GL','PR_CT','PR_IC','PR_ME','PR_SD','PR_OS','PR_SH']}

data_type_string  = ['PR_XB','PR_BA','PR_TE','PR_OC','PR_SH','PR_GL']

#data_type_string  = ['PR_OC','PR_TE','PR_BA','PR_CT','PR_IC','PR_ME','PR_SD','PR_OS','PR_GL']

WMO_code_dict = {'XBT'  : ['001','002','009','011','019','021','022','031','032','039','041','042','049',
                           '051','052','059','060','061','069','071','079','081','201','202','211','212',
                           '221','222','229','231','241','251','252','401','411','421','431','451','460',
                           '461','462','481','491','501','700','710','720','730','741','742','743','751'],
                 'CTD'  : ['800','810','820','830','1017'],
                 'Seal' : ['995'], 
                 'Float': ['831','840','841','842','843','844','845','846','847','850','851','852','853','856',
                           '856','858','860','861'],
                 'All' : ['001','002','009','011','019','021','022','031','032','039','041','042','049',
                           '051','052','059','060','061','069','071','079','081','201','202','211','212',
                           '221','222','229','231','241','251','252','401','411','421','431','451','460',
                           '461','462','481','491','501','700','710','720','730','741','742','743','751',
                           '800','810','820','830','1017',
                           '831','840','841','842','843','844','845','846','847','850','851','852','853','856',
                           '856','858','860','861',
                           '995',
                           '999']}

#data_type_string  = ['PR_CT','PR_OC','PR_TE']
def get_duplicate_depth_index(depths):

    unique_vals, inverse, count = np.unique(depths, return_inverse=True,return_counts=True)
    idx_vals_repeated = np.where(count > 1)[0]
    if 0==len(idx_vals_repeated):
        
        return []

    else: 
        vals_repeated = unique_vals[idx_vals_repeated]
        idx_repeated  = []
        for i_rep_val in vals_repeated:
            idx_repeated.append(np.nonzero(depths==i_rep_val)[0])
    return idx_repeated



def compound_logical(data,condition):
    data = data.tolist()
    n_conditions = len(condition)
    matching_indicies  = []
    found_data = False

    for i_cond in range(0,n_conditions):
        condition_indicies = [i for i,n in enumerate(data) if n.strip() == condition[i_cond]]
        if len(condition_indicies) != 0:
            for idx in condition_indicies:
               matching_indicies.append(idx)

    return sorted(matching_indicies)

if __name__ == '__main__':

    #base_file_path  = '/OSM/CBR/OA_DCFP/data3/observations/CORA/legacy/CORA_50/unpacked/home/cercache/users/mirror/home/oo9/oo/CORA4.3/Final_patched'
    base_file_path  = '/OSM/CBR/OA_DCFP/data2/observations/CORA/CORA_50/unpacked/home/cercache/users/mirror/home/oo9/oo/CORA4.3/Final_patched/'
#    base_file_path  = '/OSM/CBR/OA_DCFP/work/cha674/CORA_interrogation/test_files/'
    platform_type   = 'All'
    CORA_VERSION    = 50
    variable_to_get = 'salinity'

    MAX_DEPTH_TO_COMPUTE_STATS = 2000
    START_YEAR  = 2014
    END_YEAR    = 2016

    file_to_read = {str(START_YEAR) : []}
    total_num_profiles_for_year = {str(START_YEAR) : 0}
    for i_year in range(START_YEAR,END_YEAR):
        file_to_read[str(i_year)] = []    
        total_num_profiles_for_year[str(i_year)] = 0
 
    total_num_profiles  = 0
    n_days_in_database  = 0
    n_files  = 0

    for i_year in range(START_YEAR,END_YEAR):
        data_path_for_current_year = os.path.join(base_file_path,str(i_year))
        dir_contents = os.listdir(data_path_for_current_year)
        dir_contents.sort()
        first_pass = True
        total_num_profiles_current_year = 0

        for entry in dir_contents:
            for i_file_type in data_type_dict[platform_type]:
                if os.path.isfile(os.path.join(data_path_for_current_year,entry)) and entry.endswith(i_file_type + ".nc"):
                    #print(entry)
                    file_handle  = xarray.open_dataset(os.path.join(data_path_for_current_year,entry), decode_times=True)
                    WMO_inst_type = file_handle['WMO_INST_TYPE'].values.astype('str')
                    WMO_type = WMO_inst_type.dtype
                    if platform_type == 'All':
                        idx_to_get = file_handle['N_PROF'].values
                    
                    else:
                        idx_to_get = compound_logical(WMO_inst_type,WMO_code_dict[platform_type])
                    if first_pass:
                        dates  = pd.to_datetime(file_handle['JULD'][idx_to_get].values).date
                        first_pass=False
                    else: 
                        dates = np.concatenate([dates,pd.to_datetime(file_handle['JULD'][idx_to_get].values).date])
                    

                    variable_list = file_handle.data_vars
                    
                    if ((variable_to_get.lower() == 'temperature') or (variable_to_get.lower() == 'temp')) and 'TEMP' in variable_list:
            
                        var     = file_handle['TEMP'][idx_to_get,:]
                        n_profiles_current_file = np.logical_not(np.all(np.isnan(var),axis=1)).values.sum()

                    elif ((variable_to_get == 'salinity') or (variable_to_get.lower() == 'salt')) and 'PSAL' in variable_list:

                        var     = file_handle['PSAL'][idx_to_get,:]
                        n_profiles_current_file = np.logical_not(np.all(np.isnan(var),axis=1)).values.sum()

                    else:
                        n_profiles_current_file = 0
                    
                    
                    total_num_profiles_current_year = total_num_profiles_current_year + n_profiles_current_file
                    
                    #END if n_profiles !=0
                    file_handle.close()
                    if n_profiles_current_file !=0:
                        file_to_read[str(i_year)].append(os.path.join(data_path_for_current_year,entry))         
                #END if os.path
            #END for i_file_type in data_type_string
        #END for entry in dir_contents
        file_to_read[str(i_year)].sort()

        if i_year == START_YEAR:
            unique_dates = {str(i_year) : np.sort(np.unique(dates))}
        else:
            unique_dates[str(i_year)] = np.sort(np.unique(dates))

        n_days_in_database = n_days_in_database + len(unique_dates[str(i_year)])
        
        n_files = n_files + len(file_to_read[str(i_year)])
        total_num_profiles_for_year[str(i_year)] = total_num_profiles_current_year
        total_num_profiles = total_num_profiles + total_num_profiles_current_year
    #END for i_year 
    #print(file_to_read)    
    print('==============================================================')
    print('Total number of files: ', n_files)
    print('Total number of profiles: ', total_num_profiles)
    print('Total number of unique dates in database:', n_days_in_database)
    print('==============================================================')
#    file_of_type_to_get.sort()
#    n_points_at_depth
#    for i_year in range(START_YEAR,END_YEAR):
#        print(total_num_profiles_for_year[str(i_year)])

    print(total_num_profiles_for_year)


    for i_year in range(START_YEAR,END_YEAR):
    
        #data_path_for_current_year = os.path.join(base_file_path,str(i_year))
        #dir_contents = os.listdir(data_path_for_current_year)
        first_pass = True
        total_num_profiles_current_year = 0

        
        print('============================')
        print('Year: ', i_year)
        print('Total number of profiles for year: ', total_num_profiles_for_year[str(i_year)]) 
        profile_counter = 0
        latitude  = np.nan * np.zeros(total_num_profiles_for_year[str(i_year)],dtype=np.float32) 
        longitude = np.nan * np.zeros(total_num_profiles_for_year[str(i_year)],dtype=np.float32)
        time      = np.zeros(total_num_profiles_for_year[str(i_year)],dtype='datetime64[ns]')

        WMO_inst_code  = np.zeros(total_num_profiles_for_year[str(i_year)],dtype=WMO_type)
        max_depth      = np.zeros(total_num_profiles_for_year[str(i_year)],dtype=np.float32)

        files_for_current_year = file_to_read[str(i_year)]
        for i_file in files_for_current_year: 

            file_handle  = xarray.open_dataset(i_file, decode_times=True)
            n_levels            = file_handle['N_LEVELS'].size
            n_profiles_for_file = file_handle['N_PROF'].size
            WMO_inst_type = file_handle['WMO_INST_TYPE'].values.astype('str')
            
                    
            if platform_type == 'All':
                idx_to_get = file_handle['N_PROF'].values
            else:
                idx_to_get = compound_logical(WMO_inst_type,WMO_code_dict[platform_type])
                   
            WMO_inst_type = WMO_inst_type[idx_to_get] 

            variable_list = file_handle.data_vars
            if ((variable_to_get.lower() == 'temperature') or (variable_to_get.lower() == 'temp')) and 'TEMP' in variable_list:
                var  = file_handle['TEMP'][idx_to_get,:]
            elif ((variable_to_get == 'salinity') or (variable_to_get.lower() == 'salt')) and 'PSAL' in variable_list:
                var  = file_handle['PSAL'][idx_to_get,:]
            

            good_profile_idx = np.nonzero(np.logical_not(np.all(np.isnan(var),axis=1)).values)[0]                        
            n_good_profiles = good_profile_idx.size
             
            current_latitudes = file_handle['LATITUDE'][idx_to_get][good_profile_idx].values
            current_longitudes = file_handle['LONGITUDE'][idx_to_get][good_profile_idx].values 
                                        
            if 'DEPH' in variable_list:
                depth    = file_handle['DEPH'][idx_to_get,:][good_profile_idx,:].values
                vertical_coord_QC = file_handle['DEPH_QC'][idx_to_get,:][good_profile_idx,:].values

            if 'PRES' in variable_list:
                pressure          = file_handle['PRES'][idx_to_get,:][good_profile_idx,:].values
                vertical_coord_QC = file_handle['PRES_QC'][idx_to_get,:][good_profile_idx,:].values
            
                lat_broadcast = np.tile(current_latitudes,[1,n_levels]).reshape([n_good_profiles,n_levels])
                depth_from_pressure = -TEOS_10.z_from_p(pressure, lat_broadcast)
            
            if ('DEPH' in variable_list) and ('PRES' in variable_list):
            
                bad_profile_depth_idx = np.nonzero(np.all(np.isnan(depth),axis=1))[0]
                bad_profile_press_idx = np.nonzero(np.all(np.isnan(pressure),axis=1))[0]
                
                for i_bad_depth_profile in bad_profile_depth_idx:
                    if i_bad_depth_profile not in bad_profile_press_idx:
                        depth[i_bad_depth_profile,:] = depth_from_pressure[i_bad_depth_profile,:]
            if ('DEPH' not in variable_list) and ('PRES' in variable_list): 
               depth = depth_from_pressure

            bad_profile_depth_idx = np.nonzero(np.all(np.isnan(depth),axis=1))[0]
            #print(np.nanmax(depth,axis=1)) 
            max_depth[profile_counter:profile_counter+n_good_profiles] = np.nanmax(depth,axis=1)

            current_latitudes[bad_profile_depth_idx] = np.nan
            current_longitudes[bad_profile_depth_idx] =np.nan 
            latitude[profile_counter:profile_counter+n_good_profiles]  = current_latitudes
            longitude[profile_counter:profile_counter+n_good_profiles] = current_longitudes
            time[profile_counter:profile_counter+n_good_profiles]           =   file_handle['JULD'][good_profile_idx]
            WMO_inst_code[profile_counter:profile_counter+n_good_profiles]  = WMO_inst_type[good_profile_idx]
           
            profile_counter = profile_counter + n_good_profiles 
        #END for entry in dir_contents


        output_file_path = '/OSM/CBR/OA_DCFP/work/cha674/CORA_interrogation/Stat_files_v' + str(CORA_VERSION) + '/V2_after_bug_fix/' 
        output_file_name = 'CORA_v' + str(CORA_VERSION) + '_' + variable_to_get + '_' + str(i_year) + '_stats_' + platform_type + 'QC012.fix2.nc'

        print('Writing file: ', output_file_name, ' to ', output_file_path)

        output_dataset = xarray.DataArray(latitude,dims=('N_PROF'),coords={'N_PROF':np.arange(0,latitude.size)}).to_dataset(name='latitudes')
        output_dataset['longitudes'] = xarray.DataArray(longitude,dims=('N_PROF'),coords={'N_PROF':np.arange(0,latitude.size)})
        output_dataset['JULD']       = xarray.DataArray(time,dims=('N_PROF'),coords={'N_PROF':np.arange(0,latitude.size)})
        output_dataset['max_depth']  = xarray.DataArray(max_depth,dims=('N_PROF'),coords={'N_PROF':np.arange(0,latitude.size)})
        output_dataset['WMO_instrument_code']  = xarray.DataArray(WMO_inst_code,dims=('N_PROF'),coords={'N_PROF':np.arange(0,latitude.size)}) 

        output_dataset.to_netcdf(os.path.join(output_file_path,output_file_name))

    #END for i_year


 


    dsa 
    for i_year in range(START_YEAR,END_YEAR):
        print('============================')
        print('Year: ', i_year)
        print('Total number of profiles for year: ', total_num_profiles_for_year[str(i_year)]) 
        profile_counter = 0
        latitude  = np.nan * np.zeros(total_num_profiles_for_year[str(i_year)],dtype=np.float32) 
        longitude = np.nan * np.zeros(total_num_profiles_for_year[str(i_year)],dtype=np.float32)
        time      = np.zeros(total_num_profiles_for_year[str(i_year)],dtype=np.float64)

        WMO_inst_code  = np.zeros(total_num_profiles_for_year[str(i_year)],dtype=np.int32)
        max_depth      = np.zeros(total_num_profiles_for_year[str(i_year)],dtype=np.float32)

        n_points_on_level = np.zeros([len(unique_dates[str(i_year)]),interp_levels.size],dtype=np.int32)

        n_files_for_year = len(file_of_type_to_get[str(i_year)])


        data_path_for_current_year = os.path.join(base_file_path,str(i_year))
        for i_file in range(0,n_files_for_year): 
       
            print("Opening file: ", i_file, ' of ', n_files_for_year,': ', file_of_type_to_get[str(i_year)][i_file])        

            file_handle  = xarray.open_dataset(os.path.join(data_path_for_current_year, file_of_type_to_get[str(i_year)][i_file]), decode_times=True)
            n_levels     = file_handle['N_LEVELS'].size
            WMO_inst_type = file_handle['WMO_INST_TYPE'].values.astype('str')
        
            idx_to_get = compound_logical(WMO_inst_type,WMO_code_dict[platform_type])
            n_profiles = len(idx_to_get)
            
            if n_profiles==0:
                continue

            current_latitude                                          = file_handle['LATITUDE'][idx_to_get].values
            current_longitude                                         = file_handle['LONGITUDE'][idx_to_get].values
            time_current_file                                         = file_handle['JULD'][idx_to_get].values              
            time [profile_counter:profile_counter+n_profiles]         = time_current_file
            WMO_inst_code[profile_counter:profile_counter+n_profiles] = WMO_inst_type[idx_to_get].astype(int)

            latitude[profile_counter:profile_counter+n_profiles]      = file_handle['LATITUDE'][idx_to_get].values
            longitude[profile_counter:profile_counter+n_profiles]     = file_handle['LONGITUDE'][idx_to_get].values
            current_dates                                             = pd.to_datetime(time_current_file).date 

            variable_list = file_handle.data_vars
            if 'DEPH' in variable_list:
                depth    = file_handle['DEPH'][idx_to_get,:].values
                vertical_coord_QC = file_handle['DEPH_QC'][idx_to_get,:]

            elif 'PRES' in variable_list:
                pressure          = file_handle['PRES'][idx_to_get,:].values
                vertical_coord_QC = file_handle['PRES_QC'][idx_to_get,:]
            
                lat_broadcast = np.tile(latitude[profile_counter:profile_counter+n_profiles],[1,n_levels]).reshape([n_profiles,n_levels])
                depth = -TEOS_10.z_from_p(pressure, lat_broadcast)
            #END if 'DEPH' in variable_list
            max_depth[profile_counter:profile_counter+n_profiles] = np.nanmax(depth,axis=1)

            if (variable_to_get.lower() == 'temperature') or (variable_to_get.lower() == 'temp'):
                if 'TEMP' in variable_list:
        
                    var     = file_handle['TEMP'][idx_to_get,:]
                    var_QC  = file_handle['TEMP_QC'][idx_to_get,:]
                else: 
                    continue
            elif (variable_to_get == 'salinity') or (variable_to_get.lower() == 'salt'):
                if 'PSAL' in variable_list:
                    var     = file_handle['PSAL'][idx_to_get,:]
                    var_QC  = file_handle['PSAL_QC'][idx_to_get,:]
                else: 
                    continue

 
            for i_profile in range(0,n_profiles):
#                print(i_profile)
                date_of_profile = current_dates[i_profile]
                idx_date = np.nonzero(unique_dates[str(i_year)]==date_of_profile)[0][0]
            
            
                profile_current = var[i_profile,:]
                QC_profile_current = var_QC[i_profile,:]
                vertical_coord_QC_profile_current = vertical_coord_QC[i_profile,:]

                profile_current = profile_current.where((QC_profile_current.astype(float)==0) | (QC_profile_current.astype(float)==1) | (QC_profile_current.astype(float)==2)) 
                profile_current = profile_current.where((vertical_coord_QC_profile_current.astype(float)==0) | (vertical_coord_QC_profile_current.astype(float)==1) | (vertical_coord_QC_profile_current.astype(float)==2)) 

                idx_duplicate_depths = get_duplicate_depth_index(depth[i_profile,:])
                if len(idx_duplicate_depths) != 0:
                    for i_duplicate_index in idx_duplicate_depths:
                        for i_index in range(1,len(i_duplicate_index)):

                            depth[i_profile,i_duplicate_index[i_index]]   = depth[i_profile,i_duplicate_index[i_index]] + 0.01*float(i_index)
                    #END for i_duplicate_index
                #END if len(idx_duplicate_depths) !=0
            
                n_good_points = (1*profile_current.notnull().values).sum()
                
                if n_good_points<5:
                    continue
                else: 

                    profile_current['N_LEVELS'] = np.sort(depth[i_profile,:])
                    first_good_depth_var   = profile_current.to_series().first_valid_index()
                    last_good_depth_var    = profile_current.to_series().last_valid_index()
                    first_good_depth_depth = profile_current['N_LEVELS'].to_series().first_valid_index()
                    last_good_depth_depth  = profile_current['N_LEVELS'].to_series().last_valid_index()

                    first_good_depth = max(first_good_depth_var,first_good_depth_depth)
                    last_good_depth  = max(last_good_depth_var,last_good_depth_depth)

                    first_good_idx   = np.nonzero(profile_current['N_LEVELS'].values==first_good_depth)[0][0] 
                    last_good_idx    = np.nonzero(profile_current['N_LEVELS'].values==last_good_depth )[0][0]
                    
                    if np.any(profile_current['N_LEVELS'][first_good_idx:last_good_idx+1].isnull()):
#                        print('Hello')
                        depth_tmp = depth[i_profile,:]
                        
                        depth_tmp[first_good_idx:last_good_idx] = pd.Series(depth_tmp[first_good_idx:last_good_idx+1]).interpolate().values
                        profile_current['N_LEVELS'] = depth_tmp
#                    print(last_good_depth)
#                    print(first_good_depth)
#                    print('======')
                    if first_good_depth>MAX_DEPTH_TO_COMPUTE_STATS:
                        first_standard_level =interp_levels.size
                    else:  
                        first_standard_level = np.nonzero(interp_levels>=first_good_depth)[0][0]
                    
                    if last_good_depth > MAX_DEPTH_TO_COMPUTE_STATS:
                        last_standard_level = interp_levels.size
                    else:
                        last_standard_level  = np.nonzero(interp_levels>=last_good_depth)[0][0]
                    good_levels = np.ones([last_standard_level-first_standard_level])
                    #print(first_good_depth)
                    #print(last_good_depth) 
                    #print(first_standard_level)
                    #print(last_standard_level)
                    n_points_on_level[idx_date,first_standard_level:last_standard_level] = n_points_on_level[idx_date,first_standard_level:last_standard_level] + good_levels
 
                    #try:
                    #    profile_current = profile_current[first_good_idx:last_good_idx].interp(N_LEVELS=interp_levels,method='nearest')
                    #except: 
                    #    profile_curren = np.nan * interp_levels
                    
                    #n_points_on_level[idx_date,:] = n_points_on_level[idx_date,:] +  1*profile_current.notnull().values
 
                 #END if n_good_points<5:
            #END for i_profile
            profile_counter = profile_counter + n_profiles 
            file_handle.close()
        #END for i_file
   
        n_points_on_level[:,0] = n_points_on_level[:,1]
        #output_file_path = '/OSM/CBR/OA_DCFP/work/cha674/CORA_interrogation/Stat_files_v51/' 
        #output_file_name = 'CORA_v51_' + variable_to_get + '_' + str(i_year) + '_stats_' + platform_type + 'QC012.npz'

        output_file_path = '/OSM/CBR/OA_DCFP/work/cha674/CORA_interrogation/Stat_files_v' + str(CORA_VERSION) + '/Simple_Counts/' 
        output_file_name = 'CORA_v' + str(CORA_VERSION) + '_' + variable_to_get + '_' + str(i_year) + '_stats_' + platform_type + 'QC012.simple_count_new.npz'

        print("Saving file: ", output_file_path + output_file_name)
        np.savez(output_file_path + output_file_name, n_points_on_level=n_points_on_level, time=time,longitude=longitude,latitude=latitude,unique_dates=unique_dates[str(i_year)],WMO_inst_code=WMO_inst_code,max_depth=max_depth)

    #END for i_year
    
