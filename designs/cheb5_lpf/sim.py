import sys, numpy as np
sys.path.insert(0, r"c:\Users\acnb7\Documents\RA_Work\workspace\AWRMWO-mcp-v2\tests")
import rf_theory as rt
from scipy.optimize import minimize
H=0.8e-3; ER=4.4; TD=0.02; T=35e-6; C0=299792458.0
g=[1.1468,1.3712,1.9750,1.3712,1.1468]
def weff(w):  # Hammerstad thickness correction (w/h>1/2pi)
    return w+T/np.pi*(1+np.log(2*H/T))
def line(w,L,f):
    we=weff(w); z,ee0=rt.ms_analysis(we,H,ER)
    ee=rt.ms_eeff_kj(we,H,ER,f)
    # dispersion of Z ignored (shortcut)
    k0=2*np.pi*f/C0
    ad=k0*ER*(ee-1)*TD/(2*np.sqrt(ee)*(ER-1))
    rs=np.sqrt(np.pi*f*4e-7*np.pi/5.8e7)
    ac=rs/(z*we)
    gam=ad+ac+1j*k0*np.sqrt(ee)
    gl=gam*L
    return rt._abcd(np.cosh(gl),z*np.sinh(gl),np.sinh(gl)/z,np.cosh(gl)), z, ee0
def s_of(ws,Ls,f):
    M=rt.cascade(*[line(w,L,f)[0] for w,L in zip(ws,Ls)])
    s11,s21,_,_=rt.abcd_to_s(M); return s11,s21
def widths(zh,zl): return rt.ms_synthesis(zh,H,ER)-0, rt.ms_synthesis(zl,H,ER)
def design(zh,zl,f0=2e9):
    # zero-T widths for synthesis, then find w giving Z with thickness correction
    from scipy.optimize import brentq
    wh=brentq(lambda w: rt.ms_analysis(weff(w),H,ER)[0]-zh,0.05e-3,3e-3)
    wl=brentq(lambda w: rt.ms_analysis(weff(w),H,ER)[0]-zl,0.3e-3,20e-3)
    ws=[wl,wh,wl,wh,wl]  # g1 shunt C(low), g2 series L(high)...
    Ls=[]
    for gi,w in zip(g,ws):
        z,ee=line(w,1,f0)[1:]
        ee=rt.ms_eeff_kj(weff(w),H,ER,f0)
        th=gi*zl/50 if w==wl else gi*50/zh
        Ls.append(th/(2*np.pi*f0*np.sqrt(ee)/C0))
    return ws,Ls
f=np.arange(0.1e9,6.0001e9,10e6)
def metrics(ws,Ls):
    s11,s21=s_of(ws,Ls,f)
    p=(f<=1.8e9)
    return rt.db(s21)[p].min(), rt.db(s11)[p].max(), rt.db(s21)[np.argmin(abs(f-4e9))]
if __name__=="__main__":
    for zh,zl in [(100,15),(110,15),(120,12),(120,15),(130,10),(100,12)]:
        ws,Ls=design(zh,zl)
        print(zh,zl,[round(w*1e3,3) for w in ws],[round(l*1e3,2) for l in Ls],[round(x,2) for x in metrics(ws,Ls)])
