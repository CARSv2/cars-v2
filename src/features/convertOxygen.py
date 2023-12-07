# convert the oxygen concentration from umole/L to mole/kg'3
import gsw
import pandas

# not a functioning script yet, here so I don't lose it.
# assumes a dataframe with columns labelled SALINITY TEMPERATURE OXYGEN
sal = data['SALINITY']
temp = data['TEMPERATURE']
oxy = data['OXYGEN']
SA = gsw.conversions.SA_from_SP(sal, press, lon, lat)
CT = gsw.conversions.CT_from_t(SA,temp,press)
pdens = gsw.density.rho(SA,CT,press)
# convert from volume to mass
newoxy = oxy/pdens
# now from umol to mole
newoxy = newoxy * 1e-6
# assign back to dataframe
data['OXYGEN'] = newoxy