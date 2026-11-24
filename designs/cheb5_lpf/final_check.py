from sim import *
wl,wh=5.5e-3,0.215e-3
for w in (wl,wh): print(w, rt.ms_analysis(weff(w),H,ER), rt.ms_analysis(w,H,ER)[0], rt.ms_eeff_kj(weff(w),H,ER,2e9))
ws=[wl,wh,wl,wh,wl]
ws0,L0=design(110,20); L0=np.array(L0,float)
print("theory L mm",L0*1e3, metrics(ws,L0))
p=(f<=1.8e9); i4=np.argmin(abs(f-4e9))
def cost(x):
    L=np.array([x[0],x[1],x[2],x[1],x[0]])*1e-3
    s11,s21=s_of(ws,L,f)
    a=rt.db(s21);b=rt.db(s11)
    # maximise worst margin: pass loss, RL margin, stop margin
    m=min((a[p].min()+1.0)/0.3, (-12-b[p].max())/6, (-25-a[i4])/3)
    return -m
x0=[L0[0]*1e3,L0[1]*1e3,L0[2]*1e3]
r=minimize(cost,x0,method="Nelder-Mead",bounds=[(v*0.7,v*1.4) for v in x0])
x=np.round(r.x,2); print("opt",x0,r.x,x)
L=np.array([x[0],x[1],x[2],x[1],x[0]])*1e-3
print(metrics(ws,L))
for lab,ee in zip(("low","high"),(wl,wh)): print(lab, rt.ms_eeff_kj(weff(ee),H,ER,1e9),rt.ms_analysis(weff(ee),H,ER))
s11,s21=s_of(ws,L,f)
for fq in (0.1e9,1e9,1.8e9,2e9,3e9,4e9,5e9,6e9):
    k=np.argmin(abs(f-fq)); print(fq/1e9, round(float(rt.db(s21)[k]),2), round(float(rt.db(s11)[k]),2))
print("pass worst f", f[p][np.argmin(rt.db(s21)[p])], "S11 worst f", f[p][np.argmax(rt.db(s11)[p])])
# lossless
