import os
from cosi_sim.pipeline.simulate import Simulate

# Get parameters from data challene instance:
instance = Simulate("inputs.yaml")
name = instance.name

# Get working directory:
home = os.getcwd()

os.system("mkdir Simulations")
# Note: Need to scale source flux by the number of parallel sims.
for i in range(0,1000):

    this_dir = "Simulations/sim_" + str(i)
    os.system("mkdir %s" %this_dir)
    os.system("scp run_sims.py inputs.yaml %s" %this_dir)

# Make main output directory:
os.system("mkdir Output")

# Write combined tra file:
f = open("Output/%s.inc1.id1.tra" %name,"w")
f.write("TYPE TRA\n\n")

for i in range(0,1000):
        this_name = "Simulations/sim_%s/Output/%s.inc1.id1.tra.gz" %(str(i),name)
        this_file = os.path.join(home,this_name)
        f.write("IN %s\n" %this_file)

f.write("EN")
f.close()
os.system("gzip %s" %"Output/%s.inc1.id1.tra" %name)
