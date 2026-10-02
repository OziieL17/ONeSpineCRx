"""Display-only plane basis. Never use this basis to infer anatomical orientation."""
from .engine import unit, dot

def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def image_plane(matrix, dimensions, quarter_turns=0, flip_horizontal=False, flip_vertical=False):
    axes=[i for i,d in enumerate(dimensions) if d>1]
    if len(axes)!=2: raise ValueError('Se requiere una radiografía 2D; no un volumen 3D ni una línea')
    x=unit(tuple(matrix[r][axes[0]] for r in range(3)))
    raw=tuple(matrix[r][axes[1]] for r in range(3))
    y=unit(tuple(raw[i]-dot(raw,x)*x[i] for i in range(3)))
    for _ in range(quarter_turns%4): x,y=y,tuple(-v for v in x)
    if flip_horizontal: x=tuple(-v for v in x)
    if flip_vertical: y=tuple(-v for v in y)
    n=unit(cross(x,y))
    center=tuple(sum(matrix[r][i]*(dimensions[i]-1)/2 for i in range(3))+matrix[r][3] for r in range(3))
    return {'x':x,'y':y,'normal':n,'center':center}
