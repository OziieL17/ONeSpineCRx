"""Pure Python cervical geometry. Coordinates: x anterior, y cranial; no Slicer dependency."""
import math
from dataclasses import dataclass, field

VERSION = '0.1.0'
VERTEBRAE = tuple('C%d' % i for i in range(2, 8))
SEGMENTS = tuple(zip(VERTEBRAE[:-1], VERTEBRAE[1:])) + (('C7', 'T1'),)
LABELS = ['ORIGIN', 'ANTERIOR_REF', 'CRANIAL_REF'] + [v + '_' + c for v in VERTEBRAE for c in ('SA', 'SP', 'IA', 'IP')] + ['T1_SA', 'T1_SP']

def sub(a, b): return tuple(x-y for x, y in zip(a, b))
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def norm(a): return math.sqrt(dot(a, a))
def unit(a):
    n = norm(a)
    if n < 1e-8: raise ValueError('Referencia de longitud cero')
    return tuple(x/n for x in a)
def mean(points): return tuple(sum(p[i] for p in points)/len(points) for i in range(len(points[0])))
def angle(v): return math.degrees(math.atan2(v[1], v[0]))
def wrap(a): return (a+180) % 360-180

@dataclass
class Projection:
    points: dict = field(default_factory=dict)
    # mm per coordinate unit: absent until calibration is explicitly validated.
    mm_per_unit: float = None
    horizontal_confirmed: bool = False
    calibration_source: str = None
    posture: str = 'unspecified'

    def __post_init__(self):
        if self.mm_per_unit is not None and (not math.isfinite(self.mm_per_unit) or self.mm_per_unit <= 0):
            raise ValueError('Escala inválida')
        for p in self.points.values():
            if len(p) != 2 or not all(math.isfinite(x) for x in p):
                raise ValueError('Coordenadas 2D finitas requeridas')

def world_to_anatomical(points, tolerance=0.02):
    """Project RAS points on a user-confirmed image plane; do not assume screen axes.

    ORIGIN->ANTERIOR_REF defines anterior. CRANIAL_REF defines the orthogonal
    cranial half-plane. Horizontal confirmation is a separate measurement gate.
    """
    origin = points['ORIGIN']
    ux = unit(sub(points['ANTERIOR_REF'], origin))
    hint = sub(points['CRANIAL_REF'], origin)
    uy = unit(tuple(hint[i]-dot(hint, ux)*ux[i] for i in range(3)))
    scale = max(norm(sub(points['ANTERIOR_REF'], origin)), norm(hint))
    result = {}
    for key, p in points.items():
        d = sub(p, origin)
        x, y = dot(d, ux), dot(d, uy)
        residual = norm(tuple(d[i]-x*ux[i]-y*uy[i] for i in range(3)))
        if residual > max(1e-4, tolerance*scale):
            raise ValueError('Landmark fuera del plano: ' + key)
        result[key] = (x, y)
    return result

def manual_scale(a, b, length_mm):
    if not math.isfinite(length_mm) or length_mm <= 0: raise ValueError('Longitud conocida inválida')
    return length_mm / norm_nonzero(sub(a, b))

def norm_nonzero(v):
    n = norm(v)
    if n < 1e-8: raise ValueError('Calibración de longitud cero')
    return n

class GeometryModel:
    def __init__(self, projection):
        self.projection = projection
        self.bodies = {}
        self.qc = []
        for v in VERTEBRAE + ('T1',):
            body = {}
            for end, corners in [('superior', ('SA', 'SP')), ('inferior', ('IA', 'IP'))]:
                keys = [v+'_'+c for c in corners]
                if all(k in projection.points for k in keys):
                    a, p = (projection.points[k] for k in keys)
                    d = sub(a, p)
                    if d[0] <= 1e-8:
                        self.qc.append({'level': v, 'code': 'AP_ORDER', 'message': 'Revisar anterior/posterior o platillo vertical'})
                        continue
                    body[end] = {'anterior': a, 'posterior': p, 'midpoint': mean([a,p]), 'axis': unit(d), 'width': norm(d), 'angle_deg': angle(d)}
            if all(e in body for e in ('superior', 'inferior')):
                s, i = body['superior'], body['inferior']
                # Verify separation over the overlapping horizontal support.
                lo = max(s['posterior'][0], i['posterior'][0])
                hi = min(s['anterior'][0], i['anterior'][0])
                if hi <= lo or min(self.line_y(s,lo)-self.line_y(i,lo), self.line_y(s,hi)-self.line_y(i,hi)) <= 0:
                    self.qc.append({'level':v, 'code':'BODY_GEOMETRY', 'message':'Platillos cruzados, invertidos o sin soporte común'})
                    continue
                body['centroid'] = mean([s['anterior'],s['posterior'],i['anterior'],i['posterior']])
            if body: self.bodies[v] = body

    @staticmethod
    def line_y(end, x):
        p, a = end['posterior'], end['anterior']
        return p[1]+(x-p[0])*(a[1]-p[1])/(a[0]-p[0])

    def end(self, v, which): return self.bodies.get(v, {}).get(which)

    def disc(self, cranial, caudal):
        top, bottom = self.end(cranial,'inferior'), self.end(caudal,'superior')
        if not top or not bottom: return None
        u = bottom['axis']
        n = (-u[1], u[0]) # cranial normal
        origin = bottom['posterior']
        # Intersections with normals over actual shared endplate support, no extrapolation.
        top_a, top_p = sub(top['anterior'],origin), sub(top['posterior'],origin)
        xa, xp = dot(top_a,u), dot(top_p,u)
        if xa-xp <= 1e-8: return None
        lo, hi = max(0,xp), min(bottom['width'],xa)
        if hi-lo <= 1e-8: return {'status':'no_overlap'}
        heights = {}
        for label, f in [('posterior',0),('25',.25),('50',.5),('75',.75),('anterior',1)]:
            x = lo+(hi-lo)*f
            t = (x-xp)/(xa-xp)
            pos = tuple(top_p[i]+t*(top_a[i]-top_p[i]) for i in range(2))
            heights[label] = dot(pos,n)
        if min(heights.values()) <= 0: return {'status':'crossed_endplates'}
        return {'status':'ok', 'iva_deg':wrap(top['angle_deg']-bottom['angle_deg']),
                'height_units':heights, 'mean_height_units':sum(heights.values())/5,
                'translation_units':dot(sub(top['posterior'],bottom['posterior']),u),
                'ap_reference_units':bottom['width'],
                'overlap_fraction':(hi-lo)/bottom['width'],
                'debug':{'origin':origin,'axis':u,'normal':n,'support_interval':[lo,hi],
                         'cranial_posterior':top['posterior'],'caudal_posterior':bottom['posterior']}}

def measurement(value=None, unit=None, reason=None, method=None):
    return {'value':value, 'unit':unit, 'status':'ok' if value is not None else 'unavailable', 'reason':reason, 'method':method}

def analyze(projection):
    g = GeometryModel(projection)
    out = {'global':{}, 'segments':{}, 'qc':g.qc, 'geometry':g.bodies,
           'metadata':{'horizontal_confirmed':projection.horizontal_confirmed, 'mm_per_unit':projection.mm_per_unit,
                       'calibration_source':projection.calibration_source, 'posture':projection.posture}}
    scale = projection.mm_per_unit
    global_ = out['global']
    c2, c7, t1 = g.end('C2','inferior'), g.end('C7','inferior'), g.end('T1','superior')
    cl = wrap(c2['angle_deg']-c7['angle_deg']) if c2 and c7 else None
    global_['CL_C2_C7_deg'] = measurement(cl,'deg', 'C2/C7 inferior no disponibles' if cl is None else None,'signed inferior-endplate Cobb; lordosis positive')
    for name, end in [('C2_slope_deg',c2), ('C7_slope_deg',g.end('C7','superior')), ('T1_slope_deg',t1)]:
        value = -end['angle_deg'] if end and projection.horizontal_confirmed else None
        global_[name] = measurement(value,'deg','Requiere platillo y horizontal confirmada' if value is None else None,'anterior down positive')
    ts = global_['T1_slope_deg']['value']
    global_['T1S_minus_CL_deg'] = measurement(ts-cl if ts is not None and cl is not None else None,'deg','Requiere T1S y CL' if ts is None or cl is None else None)
    center = g.bodies.get('C2',{}).get('centroid')
    c7s = g.end('C7','superior')
    valid_sva = center and c7s and scale is not None and projection.horizontal_confirmed
    global_['cSVA_C2_C7_mm'] = measurement((center[0]-c7s['posterior'][0])*scale if valid_sva else None,'mm',
        None if valid_sva else 'Requiere centro C2, C7_SP, calibración y horizontal','four-corner C2 centroid approximation to C7_SP; anterior positive')
    for cranial, caudal in SEGMENTS:
        key = cranial+'_'+caudal
        d = g.disc(cranial,caudal)
        if not d or d['status'] != 'ok':
            reason = 'Landmarks faltantes' if not d else d['status']
            out['segments'][key] = {'status':'unavailable','reason':reason}
            if d: out['qc'].append({'level':key,'code':d['status'],'message':'Revisar soporte y platillos'})
            continue
        s = {'status':'ok', 'IVA_deg':measurement(d['iva_deg'],'deg',method='cranial inferior minus caudal superior'),
             'translation_mm':measurement(d['translation_units']*scale if scale else None,'mm',None if scale else 'Sin calibración'),
             'translation_pct':measurement(100*d['translation_units']/d['ap_reference_units'],'%',method='posterior corners on caudal superior axis / caudal AP width'),
             'disc_height_mm':{k:measurement(v*scale if scale else None,'mm',None if scale else 'Sin calibración') for k,v in d['height_units'].items()},
             'mean_disc_height_mm':measurement(d['mean_height_units']*scale if scale else None,'mm',None if scale else 'Sin calibración'),
             'overlap_fraction':d['overlap_fraction'], 'debug':d['debug']}
        # Explicit exploratory ratio; not a named validated cervical DHI/IHI formula.
        s['disc_height_AP_ratio_pct'] = measurement(100*d['mean_height_units']/d['ap_reference_units'],'%',method='exploratory mean normal height / caudal superior AP width')
        out['segments'][key] = s
    if not projection.horizontal_confirmed: out['qc'].append({'code':'HORIZONTAL_UNCONFIRMED','message':'Pendientes slopes y cSVA'})
    if scale is None: out['qc'].append({'code':'UNCALIBRATED','message':'Pendientes distancias mm; ángulos y razones disponibles'})
    incomplete = any(m['status'] != 'ok' for m in global_.values()) or any(s['status'] != 'ok' for s in out['segments'].values())
    out['state'] = 'partial' if incomplete or out['qc'] else 'review_required'
    return out

def dynamic(flex, ext):
    """Signed EXT-FLEX and absolute excursion, only like-for-like available values."""
    def delta(a,b):
        if a.get('value') is None or b.get('value') is None:
            return {'delta_ext_minus_flex':None,'excursion':None,'unit':a.get('unit'),'status':'unavailable'}
        d = b['value']-a['value']
        return {'delta_ext_minus_flex':d,'excursion':abs(d),'unit':a['unit'],'status':'ok'}
    result = {'convention':'EXT minus FLEX', 'global':{}, 'segments':{}}
    for key,a in flex['global'].items(): result['global'][key] = delta(a,ext['global'][key])
    for key,a in flex['segments'].items():
        b = ext['segments'][key]
        if a['status'] != 'ok' or b['status'] != 'ok': continue
        result['segments'][key] = {name:delta(a[name],b[name]) for name in ('IVA_deg','translation_mm','translation_pct','mean_disc_height_mm')}
    # Description of observed motion, never an instability diagnosis.
    angular = [(v['IVA_deg']['excursion'],k) for k,v in result['segments'].items() if v['IVA_deg']['excursion'] is not None]
    peak = max((v for v,k in angular), default=0)
    result['largest_observed_angular_excursion'] = [k for v,k in angular if math.isclose(v,peak,abs_tol=1e-8)] if peak > 1e-8 else []
    return result

def study(projections):
    results = {name:analyze(p) for name,p in projections.items()}
    return {'schema_version':'1.0', 'software_version':VERSION, 'region':'cervical',
            'inputs':{name:{'points':p.points,'mm_per_unit':p.mm_per_unit,'horizontal_confirmed':p.horizontal_confirmed,
                            'calibration_source':p.calibration_source,'posture':p.posture} for name,p in projections.items()},
            'projections':results, 'dynamic':dynamic(results['flex'],results['ext']) if 'flex' in results and 'ext' in results else None,
            'review_status':'unreviewed'}
