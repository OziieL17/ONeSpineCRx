"""SVG figures from the same result object; no independent measurement calculations."""
from html import escape

def svg(result, projection_name):
    p = result['inputs'][projection_name]['points']
    coords = [v for k,v in p.items() if k not in ('ORIGIN','ANTERIOR_REF','CRANIAL_REF')]
    if not coords: raise ValueError('No hay landmarks anatómicos')
    xmin,xmax = min(v[0] for v in coords),max(v[0] for v in coords)
    ymin,ymax = min(v[1] for v in coords),max(v[1] for v in coords)
    scale = min(410/max(xmax-xmin,1),650/max(ymax-ymin,1))
    def xy(v): return (50+(v[0]-xmin)*scale,80+(ymax-v[1])*scale)
    def line(a,b,color='#19677b'):
        x,y=xy(a); xx,yy=xy(b)
        return '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="2"/>' % (x,y,xx,yy,color)
    items=['<svg xmlns="http://www.w3.org/2000/svg" width="1050" height="850" viewBox="0 0 1050 850">',
           '<rect width="1050" height="850" fill="#fdfdfc"/>',
           '<g font-family="sans-serif" fill="#111111"><text x="35" y="35" font-size="22">ONeSpineCRx — '+escape(projection_name.upper())+'</text>',
           '<text x="35" y="60" font-size="13">Geometría 2D · anterior a la derecha · pendiente de revisión clínica</text>']
    r = result['projections'][projection_name]
    for name,body in r['geometry'].items():
        for end in ('superior','inferior'):
            if end in body: items.append(line(body[end]['posterior'],body[end]['anterior']))
        if 'centroid' in body:
            x,y=xy(body['centroid']); items.append('<text x="%.2f" y="%.2f" font-size="15">%s</text>'%(x,y,escape(name)))
    for name,v in p.items():
        if name in ('ORIGIN','ANTERIOR_REF','CRANIAL_REF'): continue
        x,y=xy(v)
        items.append('<circle cx="%.2f" cy="%.2f" r="3" fill="#bc4673"><title>%s</title></circle>'%(x,y,escape(name)))
    for segment in r['segments'].values():
        if segment['status']=='ok':
            d=segment['debug']; items.append(line(d['cranial_posterior'],d['caudal_posterior'],'#bc4673'))
    def label(m): return '%.2f %s'%(m['value'],m['unit']) if m['value'] is not None else 'Pendiente'
    y=105
    for k,m in r['global'].items():
        items.append('<text x="520" y="%d" font-size="15">%s: %s</text>'%(y,escape(k),escape(label(m)))); y+=27
    y+=25
    for k,s in r['segments'].items():
        text=k+': pendiente' if s['status']!='ok' else '%s · IVA %s · T %s · DH %s'%(k,label(s['IVA_deg']),label(s['translation_mm']),label(s['mean_disc_height_mm']))
        items.append('<text x="520" y="%d" font-size="13">%s</text>'%(y,escape(text))); y+=27
    y+=25
    for q in r['qc'][:7]:
        items.append('<text x="520" y="%d" font-size="12" fill="#a34c00">%s</text>'%(y,escape(q['code']))); y+=20
    items.append('</g></svg>')
    return '\n'.join(items)
