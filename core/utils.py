import ezdxf
from PIL import Image, ImageDraw

def dxf_a_imagen_interna(ruta_dxf, resolucion_dpi=100):
    """
    Convierte internamente un DXF en una imagen PNG optimizada.
    """
    doc = ezdxf.readfile(ruta_dxf)
    msp = doc.modelspace()
    
    # 1. Obtener límites (Bounding Box)
    bbox = ezdxf.bbox.extents(msp)
    min_x, min_y = bbox.min.x, bbox.min.y
    max_x, max_y = bbox.max.x, bbox.max.y
    
    ancho_m = max_x - min_x
    alto_m = max_y - min_y
    
    # 2. Definir tamaño de imagen (píxeles) basado en resolución
    # Ajustamos para que no exceda límites de memoria (ej. max 4000px)
    escala = resolucion_dpi / 25.4 # puntos por mm aprox
    width_px = int(ancho_m * 10) # 10px por metro es usualmente suficiente
    height_px = int(alto_m * 10)
    
    # Crear imagen en blanco con canal alfa (transparente)
    img = Image.new("RGBA", (width_px, height_px), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # 3. Dibujar líneas del DXF en la imagen
    fact_x = width_px / ancho_m
    fact_y = height_px / alto_m
    
    for entity in msp.query('LINE LWPOLYLINE'):
        if entity.dxftype() == 'LINE':
            p1 = entity.dxf.start
            p2 = entity.dxf.end
            # Mapear coordenadas reales a píxeles de imagen
            x1 = (p1.x - min_x) * fact_x
            y1 = height_px - (p1.y - min_y) * fact_y
            x2 = (p2.x - min_x) * fact_x
            y2 = height_px - (p2.y - min_y) * fact_y
            draw.line([(x1, y1), (x2, y2)], fill=(100, 100, 100, 150), width=1)
            
    return img, (min_x, max_x, min_y, max_y)