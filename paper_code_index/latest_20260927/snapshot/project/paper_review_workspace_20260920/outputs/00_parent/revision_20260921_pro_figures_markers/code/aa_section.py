from matplotlib.patches import Rectangle
import numpy as np

def model_a(ax,annotations=False,cold_labels=False):
    def rect(x,z,w,h,fc,ec,lw=.65,zo=2):
        if w>0 and h>0:ax.add_patch(Rectangle((x,z),w,h,fc=fc,ec=ec,lw=lw,zorder=zo))
    # Fixed geometry read in the common instrument frame; no old W grid/BPE.
    for n,label,col in b.PLATES:
        v=shape(n)[1];p=xyz(n);r=v[5]
        rect(-r,p[2]+v[3],2*r,v[6]-v[3],'#F1D5B5' if 'ColdPlate' in n else '#D5DEE4','#A65E2E' if 'ColdPlate' in n else '#7E8E9A')
    for x0 in [-25.2,21.2]:
        spans=[(-19.4,-8.2),(-2.2,40.9)] if x0<0 else [(-19.4,40.9)]
        for lo,hi in spans:rect(x0,lo,4,hi-lo,'#CDEBDD','#009E73',.9,1)
    rect(-25.2,-22.4,50.4,3,'#CDEBDD','#009E73',.9,1)
    # y=0 does not intersect any gas-line bore, so the top-cap section is solid.
    rect(-25.2,40.9,50.4,1,'#CDEBDD','#009E73',.9,1)
    rect(-26,45.4,52,.3,'#D5DEE4','#7E8E9A',.7,1)
    rect(-26,-24.2,52,.3,'#D5DEE4','#7E8E9A',.7,1)
    for ri,ro,lo,hi in [(25.7,26,-23.7,45.2)]:
        for x0 in [-ro,ri]:
            for z0,z1 in ([ (lo,-7.9),(-2.5,hi)] if x0<0 else [(lo,hi)]):rect(x0,z0,ro-ri,z1-z0,'#E6EBEF','#7E8E9A',.55,1)
    for n in b.SHIELDS:
        v=shape(n+'_side_wall_above_side_port')[1];p=xyz(n+'_side_wall_above_side_port')
        cn=n+'_bottom_cap'+('_2mm' if n.startswith('SG3A') else '')
        c=shape(cn)[1];q=xyz(cn);lo=q[2]+c[6];hi=p[2]+v[6]
        for x0 in [-v[5],v[4]]:
            for z0,z1 in ([(lo,-7.9),(-2.5,hi)] if x0<0 else [(lo,hi)]):rect(x0,z0,v[5]-v[4],z1-z0,'#E6EBEF','#99A6B0',.45,1)
        rect(-v[5],q[2]+c[3],2*v[5],c[6]-c[3],'#E6EBEF','#99A6B0',.45,1)
    for part in ['Top','Bottom']:
        n='AA_W_Collimator_'+part;p=xyz(n);h=shape(n)[1]
        rect(p[0]-h[0],p[2]-h[2],2*h[0],2*h[2],'#4B5563','#222222',.5,6)
    # Actual projected silicon/support and TES layer positions.
    for i in range(6):
        n=f'Si_Substrate_Stack_side_entry_L{i}';p=xyz(n);h=shape(n)[1]
        rect(p[0]-h[0],p[2]-h[2],2*h[0],2*h[2],'#A6B3C0','#8493A0',.3,5)
        p=xyz(f'TES_L{i}');rect(p[0]-.15,p[2]-1.8,.3,3.6,'#B2182B','white',.38,8)
        for side in ['ZP','ZM']:
            n=f'Cu_SubstrateSupport_OpenRing_L{i}_{side}_panel'
            if n+'.Shape' not in b.S:continue
            p=xyz(n);h=shape(n)[1];rect(p[0]-h[0],p[2]-h[2],2*h[0],2*h[2],'#E69F00','#8A5800',.35,7)
    n='SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm';p=xyz(n)
    out=np.array(list(map(float,prop(n+'_OuterShape','Parameters').split())))
    hole=np.array(list(map(float,prop(n+'_CenterCutShape','Parameters').split())))
    for sign in [-1,1]:
        z0=p[2]+(hole[2] if sign>0 else -out[2]);rect(p[0]-out[0],z0,2*out[0],out[2]-hole[2],'#E69F00','#8A5800',.4,7)
    for y in ['YP','YM']:
        for z in ['ZP','ZM']:
            for n in [f'Cu_ColdFinger_OffAxis_{y}_{z}_from_Disk_to_Stem',f'Cu_ColdFinger_Stem_{y}_{z}_to_MXC']:
                p=xyz(n);typ,h=shape(n)
                if typ=='BRIK':
                    rect(p[0]-h[0],p[2]-h[2],2*h[0],2*h[2],'#E69F00','#8A5800',.3,5)
                elif typ=='PCON':
                    rect(p[0]-h[5],p[2]+h[3],2*h[5],h[6]-h[3],'#E69F00','#8A5800',.3,5)
                else:raise ValueError((n,typ))
    # Local Al/Bi envelopes in the same x-z section as the source sites.
    n='SE3_Al_Shield_Inner_Cylinder_2mm';p=xyz(n);v=shape(n)[1]
    for z0 in [p[2]-v[5],p[2]+v[4]]:rect(p[0]+v[3],z0,v[6]-v[3],v[5]-v[4],'#E6EBEF','#99A6B0',.45,2)
    for n,label in [('Win_Be_Vacuum_150um_side','Be'),('Win_60K_Al_foil_side','Al'),('Win_4K_Al_foil_side','Al'),('Win_Still_Al_foil_side','Al'),('Win_MagShield_Al_foil_side','Al')]:
        p=xyz(n);v=shape(n)[1]
        ax.plot([p[0],p[0]],[p[2]-v[1],p[2]+v[1]],color='#7895AB',lw=.5,zorder=3)
    ax.plot([-26,-3.4],[-5.2,-5.2],color='#6B7280',lw=.6,ls=(0,(5,3)),zorder=5)
