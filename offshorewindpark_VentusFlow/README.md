# Offshore Wind Park

## Authors
Flavio Galeazzo and Andreas Ruopp (HLRS)

## Copyright
Copyright (c) 2022-2023 High-Performance Computing Center Stuttgart (HLRS). All rights reserved.

<a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons Licence" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.

## Introduction
Wind, as a clean and renewable alternative to fossil fuels, has become an increasingly important part of the worldwide energy portfolio. New technologies allowed the manufacture of increasingly larger wind turbines with rotor diameters over 220 m and offshore installations to become mature. The wind turbines in operation in 2020 generated 7% of the world’s electricity demand [^WEA] and 16% of the electricity consumed in the European Union and United Kingdom [^WE]. 
In the analysis of wind parks, the flow around the wind turbines is dominated by small-scale fluid dynamics (< 2 km), which in turn depends on mesoscale atmosphere dynamics (< 1000 km). The successful coupling of these two scales is essential to study wind resources, along with their uncertainty and addressing the interaction of clustered wind farms. These are critical factors for the sustainable development of wind energy.
OpenFOAM has built-in models for the simulation of wind turbines and the atmospheric boundary layer, and this test case uses a modified version of the `turbinesFoam` actuator line model (ALM) external library [^turbinesFoam]. These models are used to simulate the flow over a wind park, with a focus on the power production in a challenging configuration, where the wind flows in the direction of the row of turbines.

This test case represents the offshore wind farm Westermost Rough, described by Nygaard et al. 2020 [^Nygaard]. It is located off the UK coast and consists of 35 Siemens 6 MW turbines with 154 m rotor diameter and a hub height of 102 m above sea level. Figure 1 shows the position of wind positions in the wind farm, and a snapshot of the simulations results can be seen in Figure 2.

<img src="figures/WestermostRough.png" alt="Position of the wind turbines in the Westermost Rough wind farm." width="645">

Figure 1. Position of the wind turbines in the Westermost Rough wind farm.

<img src="figures/Simulation_sample.png" alt="Visualisation of the results." height="500">

Figure 2. Visualisation of the results.

## Setup

The turbulent atmospheric boundary layer is modelled with a logarithmic wind profile coupled with a synthetic turbulence generator approach, using the `turbulentDigitalFilterInlet` velocity boundary condition, variant `digitalFilter`. The setup works for OpenFOAM v2206 onwards.

The parameters of the incoming wind profile from Nygaard et al. 2020 [^Nygaard] are a wind velocity of 8 m/s, turbulence intensity of 5.9% and meteorological wind directions between 314 and 329 degrees, which correspond to -44 to -59 degrees in cartesian coordinates. With these parameters, and assuming a logarithmic boundary layer profile with \kappa = 0.41 and z_{0} = 0.05 m, the Python script `createInletBoundaryData.py` calculates the profiles of the mean velocity UMean and the Reynolds stress tensor R in the constant/boundaryData folder. These profiles are then used by the `turbulentDigitalFilterInlet` velocity boundary condition.

The turbulence length scales of the incoming wind were estimated using results from Nandi et al. 2021 [^Nandi] for the region of interest of the wind turbines, with the length scales for the velocity component U equal to LUx = 0.5H, LUy = 0.1H, LUz=0.3H. The length scales of V and W are all equal to 0.1H. A boundary layer height H = 200 m was considered in this test case.

To model the Siemens 6 MW turbines, we used the parameters of the NREL 5MW reference wind turbine [^Jonkman], scaling the rotor up to 154 m diameter and adjusting the tip speed ratio (TSR) to 6.8 following the rated wind speed of 13 m/s and the maximum tip speed velocity of 89 m/s from public available data [^WTM].

The `turbinesFoam` actuator line model from Peter Bachant et al. [^TF] has been enhanced in the HPCWE [^HPCWE] and exaFOAM projects to use the correct blade length, to output the power in W produced by the turbine and to react dynamically to the incoming wind velocity. These enhancements can be found in this fork of `turbinesFoam` [^turbinesFoam].

The library `turbinesFoam` writes a vector field with the force of each wind turbine in a separate file in the form `force.turbineXXX`. As the current setup models 35 turbines, it generates a large number of fields in the output of each time step. To decrease the amount of output, the function `writeForceAllTurbines` called by `controlDict` sums up the fields from all wind turbines `force.turbineXXX` into a single field `forceAllTurbines`.

## Simulation Parameters

Mean velocity at hub height = 8 m/s
Turbulence intensity =  5.9 %
\kappa = 0.41
z_{0} = 0.05 m
Meteorological wind direction range from 314 to 329 degree

## Instructions

1. The test case uses an actuator line model for the wind turbines. The setup works with this fork [^turbinesFoam] of the turbinesFoam library 

`git clone https://github.com/fcgaleazzo/turbinesFoam`

`cd turbinesFoam`

`./Allwmake`

2a. Edit the script Allpre to choose the desired grid size of 12M or 103M elements 

`vi Allpre`

2b. Prepare the grid with the script Allpre

`./Allpre`

3a. If the intention is to run the test case for one single wind direction, use the script `Allrun_oneDirection`. The setup is prepared to run for 5000 time steps (2500 seconds). If the intention is to run only a few time steps for testing purposes, please edit `system/controlDict`

`./Allrun_oneDirection`

3b. If the intention is to compare the wind turbine power profile with the experimental data from Nygaard et al. 2020 [^Nygaard], use the scripts `Allpre_sixDirections` and `Allrun_sixDirections`. The setup is prepared to run for 5000 time steps (2500 seconds).

`./Allpre_sixDirections`
`./Allrun_sixDirections`

In the `validation` folder there are two scripts for the postprocessing of the simulation data of the six directions.

The python script `Allvalidate.py` reads the output of the wind turbine for each direction, and writes a `csv` file with the mean wind turbine power in W over the last 1500 s and plot the results against the experimental data, as shown in Figure 3.

<img src="figures/simulationresults.png" alt="Validation of the mean wind turbine power with experimental data from Nygaard et al. 2020 [^Nygaard]" height="500">

Figure 3. Validation of the mean wind turbine power with experimental data from Nygaard et al. 2020 [^Nygaard].

The gnuplot script `Plot_turbines.gnu` can be used to monitor the progress of the simulations, as it plots the wind turbine power evolution over time, as shown in Figure 4.

<img src="figures/Plot_turbines.png" alt="Wind turbine power evolution over time" height="500">

Figure 4. Wind turbine power evolution over time.

## Mesh and Restart Files

In order to enable restarts, meshes and corresponding developed fields are provided on the DaRUS data repository under:
https://doi.org/10.18419/darus-3975


## Known issues

The compilation of the dynamic code `writeForceAllTurbines` in parallel cases is troublesome. One solution is to run the test case in serial for only one time step, as the compiled code in the `dynamicCode` folder remains valid for further parallel runs. 

The test case uses a synthetic turbulence boundary condition of type `turbulentDigitalFilterInlet`, variant `digitalFilter`. It is known to create load imbalance in the simulation.

The `turbinesFoam` wind turbine model also creates load imbalance.

## Acknowledgment
This application has been developed as part of the exaFOAM Project https://www.exafoam.eu, which has received funding from the European High-Performance Computing Joint Undertaking (JU) under grant agreement No 956416. The JU receives support from the European Union's Horizon 2020 research and innovation programme and France, Germany, Italy, Croatia, Spain, Greece, and Portugal.

<img src="figures/Footer_Logos.jpg" alt="footer" height="100">

## References

[^WEA]: WWEA 2021: https://wwindea.org/worldwide-wind-capacity-reaches-744-gigawatts/

[^WE]: Wind Europe 2021. Wind energy in Europe: https://www.windenergyhamburg.com/fileadmin/windenergy/2022/pdf/we22_wind-europe-stats2020.pdf

[^TF]: Pete Bachant, Anders Goude, daa-mec, & Martin Wosnik. (2019). turbinesFoam/turbinesFoam: v0.1.1 (v0.1.1). Zenodo. https://doi.org/10.5281/zenodo.3542301

[^turbinesFoam]: https://github.com/fcgaleazzo/turbinesFoam, forked from https://github.com/turbinesFoam/turbinesFoam

[^WTM]: (n.d.). Siemens SWT-6.0-154. Wind-Turbine-Models.com. https://en.wind-turbine-models.com/turbines/657-siemens-swt-6.0-154

[^Jonkman]: Jonkman, J., Butterfield, S., Musial, W., & Scott, G. (2009). Definition of a 5-MW Reference Wind Turbine for Offshore System Development. In NREL Technical Report: Vol. TP-500-380. https://doi.org/10.2172/947422

[^Nygaard]: Nygaard, N. G., Steen, S. T., Poulsen, L., & Pedersen, J. G. (2020). Modelling cluster wakes and wind farm blockage. Journal of Physics: Conference Series, 1618(6), 062072. https://doi.org/10.1088/1742-6596/1618/6/062072

[^Nandi]: Nandi, T. N., & Yeo, D. (2021). Estimation of integral length scales across the neutral atmospheric boundary layer depth: A Large Eddy Simulation study. Journal of Wind Engineering and Industrial Aerodynamics, 218, 104715. https://doi.org/10.1016/j.jweia.2021.104715

[^HPCWE]: High-Performance Computing for Wind Energy. https://www.hpcwe-project.eu/

