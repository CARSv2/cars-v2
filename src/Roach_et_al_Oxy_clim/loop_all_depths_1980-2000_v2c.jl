
using NetCDF
using DIVAnd
using LinearAlgebra
using SparseArrays
using MAT
using CSV
using Preconditioners
using IterativeSolvers
using Interpolations
include("./DIVAnd_pc_ichol.jl")
include("./DIVAnd_diagapp.jl")


#Read in filenames
files=readdir("./input_for_julia/oxy/")
ftmpname="covar_input.nc"
#ENV["JULIA_DEBUG"]="all"

for ii=1:length(files)
    print(ii)
    files_o=readdir("./DIVAnd_output_oxy/1995-2005/")
    #Check if input file is a ntcdf file and make sure output file doesn't exists
    if occursin(".nc",files[ii]) && !(files[ii] in files_o)
        
        fname=joinpath(dirname(@__FILE__),"./input_for_julia/oxy/",files[ii])
        foname=joinpath(dirname(@__FILE__),"./DIVAnd_output_oxy/1995-2005/",files[ii])
        fbgname=joinpath(dirname(@__FILE__),"./DIVAnd_output_oxy/BG/",files[ii])
	fsvname=joinpath(dirname(@__FILE__),"./DIVAnd_global_statevecs/",files[ii])


        #Define constants and grid

        xg = collect(-180:.5:179.5) #collect(-180:.5:-0) collect(-150:.5:-30) collect(300:.5:400)
        yg = collect(-85:.5:85) #collect(-45:.5:45) collect(-85:.5:-20)
        xguv = ncread(fname,"xg")
        yguv = ncread(fname,"yg")
        tg = collect(1995:1:2005)
        zlvl = ncread(fname,"zlvl")
        xo = ncread(fname,"lon")
        yo = ncread(fname,"lat")
        to = ncread(fname,"time")
	obs = Float64.(ncread(fname,"oxy_anom"))
        us = ncread(fname,"u")
        vs = ncread(fname,"v")
        BG = ncread(fname,"oxy_poly");
	
	#If max(xg)>180 circshift u, v add 180deg

	#Interpolate uv onto region being processed
   	knots = (xguv,yguv)
    	itp = interpolate(knots, us, Gridded(Linear()))
    	u=itp[xg, yg]
    	itp = interpolate(knots, vs, Gridded(Linear()))
    	v=itp[xg, yg]

        #Due to memoery limitations need to add special handling for v. shallow layer, for now just run all other layers
        print(zlvl)
        if zlvl[1]>-50 && zlvl[1]<6200
        print(zlvl)

        #Make mask
        bathy =joinpath(dirname(@__FILE__),"Bathymetry","gebco_30sec_16.nc")


        xi1,yi1,mask1 = load_mask(bathy,true,xg[1:41],yg,zlvl)
	xi2,yi2,mask2 = load_mask(bathy,true,xg[42:81],yg,zlvl)
	mask=vcat(mask1,mask2)
	xg=collect(160:.5:200)
	xi,yi,fakemask = load_mask(bathy,true,xg,yg,zlvl)
        pm,pn = DIVAnd_metric(xg,yg);
        xi,yi = ndgrid(xi,yi)
        #pm=convert(Array{Float32},pm)
        #pn=convert(Array{Float32},pn)

        #Define boundary
        md=[719,0]
        mask = dropdims(mask,dims=3);

        lenx = 500000.0
        leny = lenx/2
        lent = 2.5
        epsilon = 1.0
        #lenx=convert(Array{Float32},lenx)
        #leny=convert(Array{Float32},leny)
        #lent=convert(Array{Float32},lent)
        #epsilon=convert(Array{Float32},epsilon)
        typeof(leny)

        resid= ncread(fbgname,"resid");
        print(size(resid))

        xj,yj,tj=ndgrid(xg,yg,tg);
        maski=repeat(mask,inner=[1,1,length(tg)]);
        ui=repeat(u,inner=[1,1,length(tg)]);
        vi=repeat(v,inner=[1,1,length(tg)]);
        pmi=repeat(pm,inner=[1,1,length(tg)]);
        pni=repeat(pn,inner=[1,1,length(tg)]);
        pti=fill(1.0,length(xg),length(yg),length(tg));
        mdi=[length(xg),0,0];

	nanobs=isnan.(resid)
	deleteat!(resid,findall(nanobs))
	deleteat!(xo,findall(nanobs))
	deleteat!(yo,findall(nanobs))
	deleteat!(to,findall(nanobs))

	println("Running Analysis")
        @time fij, si = DIVAndrun(maski,(pmi,pni,pti),(xj,yj,tj),(xo,yo,to),resid,(lenx,leny,lent),epsilon; velocity=(ui,vi,0*ui), moddim=mdi)
        #@time fij,si = DIVAndrun(maski,(pmi,pni,pti),(xj,yj,tj),(xo,yo,to),resid,(lenx,leny,lent),epsilon; velocity=(ui,vi,0*ui))

        nccreate(foname,"oxy_time_varying","lon",xg,"lat",yg,"time",tg,  compress=9, mode=NC_NETCDF4, t=NC_FLOAT)
        ncwrite(Float32.(fij),foname,"oxy_time_varying")
        nccreate(foname,"time_grid","time",tg,  compress=9, mode=NC_NETCDF4)
        ncwrite(tg,foname,"time_grid")

        resid=DIVAnd_residualobs(si,fij);
        
        println("Writing Resid")
        nccreate(foname,"resid","obscount",obs,  compress=9, mode=NC_NETCDF4,t=NC_FLOAT)
        ncwrite(Float32.(resid),foname,"resid")
        fij=nothing
	resid=nothing


	println("Exporting Inverse of Covariance Matrix")
	#Inverse Covar matrix is symmetric about the corner diagonal
	IX, IY, V = findnz(si.P.IS)
	#So, take data above (and including) cornor diagonal to reduce storage and I/O costs
	inds=findall(x -> x>0, IX-IY)
	IX=getindex(IX,inds)
	IY=getindex(IY,inds)
	V=getindex(V,inds)
        nccreate(foname,"invCovar","lx",IX,  compress=9, mode=NC_NETCDF4, t=NC_FLOAT)
        ncwrite(Float32.(V),foname,"invCovar")

	IX=nothing
	IY=nothing
	V=nothing
        GC.gc()
	pack2unpack=vec(reduce(hcat, si.sv.packed2unpacked))
        nccreate(fsvname,"unpackSV","lenpack",pack2unpack,  compress=9, mode=NC_NETCDF4, t=NC_INT)
        ncwrite(Int32.(pack2unpack),fsvname,"unpackSV")
	#unpack2pack=vec(reduce(hcat, si.sv.unpacked2packed))
        #nccreate(fsvname,"packSV","lenpack",unpack2pack,  compress=9, mode=NC_NETCDF4)
        #ncwrite(Int.(pack2unpack),fsvname,"unpackSV")



	#Call shell script to initiate Matlab function to produce find Variance by taking the sparse inverse subset of s.P.IS
	#@time run(`matlab -nodisplay -nosplash -nodesktop -r 'crunch_var_full; quit'`)
	#run(`rm covar_input.nc`)

	#Read statevector of relative variance at grid points from tempory file
	#file = matopen("diagCovar.mat")
	#diagcovar=Float64.(vec(read(file, "diagCovar"))) # note that this does NOT introduce a variable ``varname`` into scope
	#close(file)

	#Recast state vector to geographic coordiantes to obtain relative variance field.
        #err=unpack(si.sv,diagcovar)
        #si=nothing
        #nccreate(foname,"oxy_time_varying_err","lon",xg,"lat",yg,"time",tg, compress=9, mode=NC_NETCDF4)
        #ncwrite(err[1],foname,"oxy_time_varying_err")
	#err=nothing
	#@time errdiagapp=DIVAnd_diagapp(si.P,(pmi,pni,pti),(lenx,leny,lent),si.sv)
	#@time errcpme= DIVAnd_cpme(maski,(pmi,pni,pti),(xj,yj,tj),(xo,yo,to),resid,(lenx,leny,lent),epsilon; velocity=(ui,vi,0*ui))
        #nccreate(foname,"oxy_time_varying_err_cpme","lon",xg,"lat",yg,"time",tg,  compress=9, mode=NC_NETCDF4)
        #ncwrite(Float32.(errcpme),foname,"oxy_time_varying_err_cpme")
	#ENV["JULIA_DEBUG"]="all"
	#@time err= DIVAnd_cpme(maski,(pmi,pni,pti),(xj,yj,tj),(xo,yo,to),resid,(lenx,leny,lent),epsilon; velocity=(ui,vi,0*ui), moddim=mdi)
	#@time err,bj= DIVAnd_aexerr(maski,(pmi,pni,pti),(xj,yj,tj),(xo,yo,to),resid,(lenx,leny,lent),epsilon; velocity=(ui,vi,0*ui), moddim=mdi)
        #nccreate(foname,"oxy_time_varying_err","lon",xg,"lat",yg,"time",tg,  compress=9, mode=NC_NETCDF4)
        #ncwrite(Float64.(err),foname,"oxy_time_varying_err")
	#err=nothing

        GC.gc()
        end
    end
end
