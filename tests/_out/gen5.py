import json
M=["DB(|S(2,1)|)","DB(|S(1,1)|)","Ang(S(2,1))"]
def mk(s, build, f1=0.5e9, f2=7e9, n=1301):
    g=s+"_G"
    t=[{"tool":"set_frequencies","args":{"start_hz":f1,"stop_hz":f2,"points":n,"log":False,"document":s}},{"tool":"create_graph","args":{"name":g}}]
    t+=[{"tool":"add_measurement","args":{"graph":g,"source_doc":s,"measurement":m}} for m in M]
    t+=[{"tool":"clear_status_messages"},{"tool":"simulate"},{"tool":"wait_for_simulation","args":{"timeout_s":300}},{"tool":"graph_data","args":{"graph":g,"max_points":5000}}]
    return [{"tool":"create_schematic","args":{"name":s}}]+build+t
def E(s,m,i,p,**k): return {"tool":"add_element","args":dict(schematic=s,model=m,id=i,params=p,**k)}
def C(s,a,b): return {"tool":"connect","args":{"schematic":s,"from_pin":a,"to_pin":b}}
def P(s,pin,n,z=50): return {"tool":"add_port","args":{"schematic":s,"pin":pin,"number":n,"z0":z}}
def G(s,pin): return {"tool":"add_ground","args":{"schematic":s,"pin":pin}}
Z=70.71067811865476
out={}
s="V_TL_QWT"; out["tl_qwt"]=mk(s,[E(s,"TLIN","T1",{"Z0":Z,"EL":"90","F0":2e9},rotation=90),P(s,"T1:1",1,50),P(s,"T1:2",2,100)])
def stub(s,stubm):
    return [E(s,"TLIN","T1",{"Z0":50,"EL":"0","F0":2e9},rotation=90),E(s,stubm,"S1",{"Z0":50,"EL":"90","F0":2e9},near="T1"),
            P(s,"T1:1",1),P(s,"T1:2",2),C(s,"T1:2","S1:1")]
s="V_TL_OPEN"; out["tl_open"]=mk(s,stub(s,"TLOC"))
s="V_TL_SHORT"; out["tl_short"]=mk(s,stub(s,"TLSC"))
s="V_TL_HALF"; out["tl_half"]=mk(s,[E(s,"TLIN","T1",{"Z0":100,"EL":"180","F0":2e9},rotation=90),P(s,"T1:1",1),P(s,"T1:2",2)])
for k,v in out.items(): json.dump(v,open(f"tests/circuits/{k}.json","w"),indent=1)
