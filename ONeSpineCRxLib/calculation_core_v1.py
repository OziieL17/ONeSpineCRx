"""ONeSpineCRx Calculation Core v1 — experimental, not clinical decision support.
Pure Python 3.9 standard library. Inputs are anatomical 2D landmark coordinates.
All angles are oriented, not automatically labeled as lordosis without verified axes.
"""
import math

LEVELS = ("C2", "C3", "C4", "C5", "C6", "C7", "T1")
EPS = 1e-9

def sub(a,b): return (a[0]-b[0],a[1]-b[1])
def dot(a,b): return a[0]*b[0]+a[1]*b[1]
def cross(a,b): return a[0]*b[1]-a[1]*b[0]
def norm(a): return math.hypot(*a)
def unit(a):
    d=norm(a)
    if d<EPS: raise ValueError("Degenerate landmark pair")
    return (a[0]/d,a[1]/d)
def angle(a,b):
    return math.degrees(math.atan2(cross(a,b),dot(a,b)))
def edge(points,level,kind):
    suffix=("IP","IA") if kind=="inferior" else ("SP","SA")
    p=points[level+"_"+suffix[0]];q=points[level+"_"+suffix[1]]
    v=sub(q,p)
    if norm(v)<EPS: raise ValueError("Zero-length endplate")
    return p,q
def segment(points,upper,lower,mm_per_unit=None):
    p,q=edge(points,upper,"inferior")
    r,s=edge(points,lower,"superior")
    u=unit(sub(s,r))
    translation=dot(sub(p,r),u)
    width=norm(sub(s,r))
    # Relative angle only; anatomical lordosis sign needs verified orientation.
    result={"iva_deg":angle(sub(q,p),sub(s,r)),
            "translation_pct":100*translation/width,
            "translation_mm":translation*mm_per_unit if mm_per_unit is not None else None,
            "ap_reference_units":width}
    # Height profile on overlap along the caudal AP axis; signed normal.
    n=(-u[1],u[0])
    t0,t1=dot(sub(p,r),u),dot(sub(q,r),u)
    lo=max(0,min(t0,t1));hi=min(width,max(t0,t1))
    if hi-lo<EPS:
        result["height_profile"]=None
        result["height_qc"]="NO_OVERLAP"
    else:
        def h(t):
            # Intersect line of cranial endplate at caudal AP coordinate t.
            f=(t-t0)/(t1-t0)
            a=(p[0]+f*(q[0]-p[0]),p[1]+f*(q[1]-p[1]))
            b=(r[0]+t*u[0],r[1]+t*u[1])
            return dot(sub(a,b),n)
        result["height_profile"]=[h(lo+(hi-lo)*k/4) for k in range(5)]
        result["height_mm"]=[v*mm_per_unit for v in result["height_profile"]] if mm_per_unit is not None else None
        result["height_ap_pct"]=[100*v/width for v in result["height_profile"]]
        result["height_qc"]="SIGNED_UNVERIFIED"
    return result

def analyze(projections):
    """projections: {lat/flex/ext:{points:{...},mm_per_unit:float|None}}."""
    out={"schema":"calculation-core-v1","status":"experimental","projections":{},"dynamic":{}}
    for name,inp in projections.items():
        pts=inp["points"];segments={};warnings=[]
        for a,b in zip(LEVELS[:-1],LEVELS[1:]):
            key=a+"_"+b
            try: segments[key]=segment(pts,a,b,inp.get("mm_per_unit"))
            except (KeyError,ValueError,ZeroDivisionError) as e:
                segments[key]={"status":"unavailable","reason":str(e)}
        # Regional angles must use direct endplate Cobb, not sum disc IVAs:
        # within-body endplate wedge makes those quantities non-equivalent.
        regional={}
        for i,a in enumerate(LEVELS[:-1]):
            for b in LEVELS[i+1:]:
                try:
                    p,q=edge(pts,a,"inferior")
                    r,s=edge(pts,b,"inferior" if b!="T1" else "superior")
                    regional[a+"_"+b]=angle(sub(q,p),sub(s,r))
                except (KeyError,ValueError): regional[a+"_"+b]=None
        out["projections"][name]={"segments":segments,"regional_cobb_deg":regional,
                                  "warnings":warnings}
    if "flex" in out["projections"] and "ext" in out["projections"]:
        f=out["projections"]["flex"]["segments"];e=out["projections"]["ext"]["segments"]
        for key in f:
            if "iva_deg" in f[key] and "iva_deg" in e[key]:
                d=(e[key]["iva_deg"]-f[key]["iva_deg"]+180)%360-180
                out["dynamic"][key]={"delta_deg":d,"excursion_deg":abs(d)}
    return out

