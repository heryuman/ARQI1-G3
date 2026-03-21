def classify_color(r, g, b):
    if max(r, g, b) < 25:
        return "oscuro"
    if abs(r - g) < 20 and abs(g - b) < 20 and max(r, g, b) > 90:
        return "blanco"
    if r > g and r > b:
        if g > 0.6 * r:
            return "amarillo"
        return "rojo"
    if g > r and g > b:
        return "verde"
    if b > r and b > g:
        return "azul"
    if r > 120 and g > 120 and b < 80:
        return "amarillo"
    return "desconocido"
