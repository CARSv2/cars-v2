

#using PyPlot

using NetCDF
using DIVAnd
using LinearAlgebra
using SparseArrays
using MAT
using CSV
include("./DIVAnd_diagapp.jl")

#Read in filenames
files=readdir("./input_for_julia/oxy/")
ftmpname="covar_input.nc"


for ii=1:length(files)
    print(ii)
    files_o=readdir("./DIVAnd_output_oxy/BG/")
    #Check if input file is a ntcdf file and make sure output file doesn't exists
    if occursin(".nc",files[ii]) && !(files[ii] in files_o)
        

        fname=joinpath(dirname(@__FILE__),"./input_for_julia/oxy/",files[ii])
        foname=joinpath(dirname(@__FILE__),"./DIVAnd_output_oxy/BG/",files[ii])

        #Define constants and grid
        println(files[ii])
        xg = ncread(fname,"xg")
        yg = ncread(fname,"yg")
        tg = collect(1990:2:2010)
        zlvl = ncread(fname,"zlvl")
        xo = ncread(fname,"lon")
        yo = ncread(fname,"lat")
        to = ncread(fname,"time")
        obs = ncread(fname,"oxy_anom")
        u = ncread(fname,"u")
        v = ncread(fname,"v")
        BG = ncread(fname,"oxy_poly");
        
	#
        println(zlvl)
        if zlvl[1]>-5 && zlvl[1]<6200
        println(zlvl)

        #Make mask
        bathy =joinpath(dirname(@__FILE__),"Bathymetry","gebco_30sec_16.nc")
	#file = matopen("surf_mask.mat")
	#surf_mask=read(file, "surf_mask")
	#close(file)
	#println(dump(surf_mask))

        xi,yi,mask = load_mask(bathy,true,xg,yg,zlvl)
        pm,pn = DIVAnd_metric(xg,yg);
        xi,yi = ndgrid(xi,yi)
        #pm=convert(Array{Float32},pm)
        #pn=convert(Array{Float32},pn)

        #Define boundary
        md=[719,0]
        mask = dropdims(mask,dims=3);
	#mask = mask + surf_mask #Mask out Arctic
	#mask=mask.>0

        lenx = 500.0*1000.0
        leny = lenx/2
        lent = 5.0
        epsilon = 1.0
	wu= 1.0
	#mask[:,341] = mask[:,1]
	#println(size(mask[:,1]))
	#println(mask[:,341])
        #Create virtual wall at northern limit of mask
	#mask

        @time fi, s = DIVAndrun(mask,(pm,pn),(xi,yi),(xo,yo),obs,(lenx,leny),epsilon; velocity=(wu*u,wu*v), moddim=md)
	#@time fi, s = DIVAndrun(mask,(pm,pn),(xi,yi),(xo,yo),obs,(lenx,leny),epsilon; velocity=(wu*u,wu*v))

	println("Writing Output")
        nccreate(foname,"oxyBG","lon",xg,"lat",yg, compress=9, mode=NC_NETCDF4)
        ncwrite(Float32.(fi),foname,"oxyBG")
        #nccreate(foname,"mask","lon",xg,"lat",yg, compress=9, mode=NC_NETCDF4)
        #ncwrite(Float32.(mask),foname,"mask")
	
	#Write out inverse of covar matrix to be evaluated in Matlab
	#Both save it to output file and write to a temporary file for matlab to read in
	println("Exporting Inverse of Covariance Matrix")
	IX, IY, V = findnz(s.P.IS)
        #nccreate(foname,"IX","lx",IX,  compress=9, mode=NC_NETCDF4)
        #ncwrite(Float32.(IX),foname,"IX")
        #nccreate(foname,"IY","lx",IX,  compress=9, mode=NC_NETCDF4)
        #ncwrite(Float32.(IY),foname,"IY")
        #nccreate(foname,"invCovar","lx",IX,  compress=9, mode=NC_NETCDF4)
        #ncwrite(Float64.(V),foname,"invCovar")
	pack2unpack=vec(reduce(hcat, s.sv.packed2unpacked))
	#CSV.write("unpack_statevec.csv",pack2unpack)
        nccreate(foname,"unpackSV","lenpack",pack2unpack,  compress=9, mode=NC_NETCDF4)
        ncwrite(pack2unpack,foname,"unpackSV")
	unpack2pack=vec(reduce(hcat, s.sv.unpacked2packed))
        nccreate(foname,"packSV","lenpack",unpack2pack,  compress=9, mode=NC_NETCDF4)
        ncwrite(pack2unpack,foname,"unpackSV")
	
        
	nccreate(ftmpname,"IX","lx",IX,  compress=9, mode=NC_NETCDF4)
        ncwrite(Float64.(IX),ftmpname,"IX")
        nccreate(ftmpname,"IY","lx",IX,  compress=9, mode=NC_NETCDF4)
        ncwrite(Float64.(IY),ftmpname,"IY")
        nccreate(ftmpname,"invCovar","lx",IX,  compress=9, mode=NC_NETCDF4)
        ncwrite(Float64.(V),ftmpname,"invCovar")
	packeddata=pack(s.sv,(fi,))
        nccreate(ftmpname,"packedfield","lx",IX,  compress=9, mode=NC_NETCDF4)
        ncwrite(Float64.(packeddata),ftmpname,"packedfield")	
        
	nccreate(foname,"IX","lx",IX,  compress=9, mode=NC_NETCDF4)
        ncwrite(Float64.(IX),foname,"IX")
        nccreate(foname,"IY","lx",IX,  compress=9, mode=NC_NETCDF4)
        ncwrite(Float64.(IY),foname,"IY")
        nccreate(foname,"invCovar","lx",IX,  compress=9, mode=NC_NETCDF4)
        ncwrite(Float64.(V),foname,"invCovar")

	#Call shell script to initiate Matlab function to produce find Variance by taking the sparse inverse subset of s.P.IS
	@time run(`matlab -nodisplay -nosplash -nodesktop -r 'crunch_var_full; quit'`)
	run(`rm covar_input.nc`)

	#Read statevector of relative variance at grid points from tempory file
	file = matopen("diagCovar.mat")
	diagcovar=Float32.(vec(read(file, "diagCovar"))) # note that this does NOT introduce a variable ``varname`` into scope
	close(file)

	#Recast state vector to geographic coordiantes to obtain relative variance field.
        err=unpack(s.sv,diagcovar)
	errcpme= DIVAnd_cpme(mask,(pm,pn),(xi,yi),(xo,yo),obs,(lenx,leny),epsilon; velocity=(u,v))
	#dump(pm)
	#pmn = (pm,pn)
	#@time errdiag =DIVAnd_diagapp(s.P,pmn,(xi,yi),s.sv)

        nccreate(foname,"oxyBGerr","lon",xg,"lat",yg, compress=9, mode=NC_NETCDF4)
        ncwrite(err[1],foname,"oxyBGerr")
        nccreate(foname,"oxyBGerrcpme","lon",xg,"lat",yg, compress=9, mode=NC_NETCDF4)
        ncwrite(errcpme,foname,"oxyBGerrcpme")


	#Write oxygen polynomial fit
        nccreate(foname,"oxypoly","lon",xg,"lat",yg,  compress=9, mode=NC_NETCDF4)
        ncwrite(Float32.(BG),foname,"oxypoly")
	
        resid=DIVAnd_residualobs(s,fi);
        
        println("Writing Resid")
        nccreate(foname,"resid","obscount",obs,  compress=9, mode=NC_NETCDF4)
        ncwrite(Float32.(resid),foname,"resid")
        fi=nothing
        s=nothing
	err=nothing
        GC.gc()
        end
    end
end
