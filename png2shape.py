import os
import sys
import potrace
import numpy as np
import xml.etree.ElementTree as ET

from PIL import Image

def resize_image(input_image_path, output_image_path, size):
    """
    Redimensiona uma imagem para o tamanho especificado.

    :param input_image_path: Caminho da imagem de entrada.
    :param output_image_path: Caminho onde a imagem redimensionada será salva.
    :param size: Tupla (largura, altura) com o novo tamanho da imagem.
    """
    # Abre a imagem
    with Image.open(input_image_path) as img:
        # Redimensiona a imagem
        resized_img = img.resize(size, Image.Resampling.LANCZOS)
        # Salva a imagem redimensionada
        resized_img.save(output_image_path)
        print(f"Imagem redimensionada salva em: {output_image_path}")

def image_to_svg(image_path, output_svg_path):
    # Carrega a imagem usando Pillow
    image = Image.open(image_path).convert('L')  # Converte para escala de cinza

    # Converte a imagem para um array numpy
    bitmap = np.array(image)

    # Inverte a imagem (Potrace espera que o fundo seja preto e o objeto branco)
    bitmap = 255 - bitmap

    # Cria um objeto Bitmap a partir do array numpy
    bmp = potrace.Bitmap(bitmap)

    # Converte o bitmap para um caminho (path) vetorial
    path = bmp.trace()

    # Escreve o SVG
    with open(output_svg_path, 'w') as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="{}" height="{}">\n'.format(image.width, image.height))
        f.write('<path d="')
        for curve in path:
            f.write('M {},{} '.format(curve.start_point.x, curve.start_point.y))
            for segment in curve:
                if segment.is_corner:
                    f.write('L {},{} L {},{} '.format(segment.c.x, segment.c.y, segment.end_point.x, segment.end_point.y))
                else:
                    f.write('C {},{} {},{} {},{} '.format(segment.c1.x, segment.c1.y, segment.c2.x, segment.c2.y, segment.end_point.x, segment.end_point.y))
            f.write('Z ')
        f.write('" fill="black" />\n')
        f.write('</svg>\n')

def convert_png_to_svg(png_path):
    """Converte a imagem PNG para SVG usando potrace."""
    # Abre a imagem e converte para preto e branco
    with Image.open(png_path) as img:
        img = img.convert("1")  # Converte para modo binário (preto e branco)
        svg_path = os.path.splitext(png_path)[0] + ".svg"

        # Usa potrace para criar o SVG
        bitmap = potrace.Bitmap(img)
        path = bitmap.trace()

        # Gera o SVG manualmente
        with open(svg_path, "w") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="{}" height="{}">\n'.format(img.width, img.height))
            for curve in path:
                f.write('<path d="')
                start = curve.start_point
                f.write('M {} {} '.format(start.x, start.y))
                for segment in curve:
                    if segment.is_corner:
                        f.write('L {} {} L {} {} '.format(
                            segment.c.x, segment.c.y,
                            segment.end_point.x, segment.end_point.y
                        ))
                    else:
                        f.write('C {} {}, {} {}, {} {} '.format(
                            segment.c1.x, segment.c1.y,
                            segment.c2.x, segment.c2.y,
                            segment.end_point.x, segment.end_point.y
                        ))
                f.write('" fill="black" />\n')
            f.write('</svg>')
        return svg_path
    
def svg_to_drawio_shape(svg_file, output_file):
    # Analisa o SVG
    tree = ET.parse(svg_file)
    root = tree.getroot()

    # Namespace do SVG (pode variar dependendo do arquivo)
    ns = {'svg': 'http://www.w3.org/2000/svg'}

    # Tamanho do shape no Draw.io (78x78 pixels)
    drawio_width = 78
    drawio_height = 78

    # Cria o root do shape do Draw.io
    shape = ET.Element('shape', {
        'name': 'custom_shape',
        'h': str(drawio_height),
        'w': str(drawio_width),
        'aspect': 'fixed',  # Mantém o aspecto fixo (não redimensionável)
        'strokewidth': 'inherit'
    })

    # Adiciona conexões (opcional)
    connections = ET.SubElement(shape, 'connections')
    for x, y in [(0.5, 0), (0.5, 1), (0, 0.5), (1, 0.5)]:
        ET.SubElement(connections, 'constraint', {
            'x': str(x),
            'y': str(y),
            'perimeter': '1'
        })

    # Adiciona background (opcional)
    background = ET.SubElement(shape, 'background')
    ET.SubElement(background, 'rect', {
        'x': '0',
        'y': '0',
        'w': str(drawio_width),
        'h': str(drawio_height)
    })

    # Adiciona foreground
    foreground = ET.SubElement(shape, 'foreground')

    # Processa elementos do SVG e converte para elementos do Draw.io
    for elem in root.findall('.//svg:*', ns):
        if elem.tag.endswith('path'):
            # Converte caminho (path) do SVG para <path> do Draw.io
            d = elem.attrib['d']
            path = ET.SubElement(foreground, 'path')

            # Divide os comandos do caminho (M, L, C, etc.)
            # Substitui vírgulas por espaços para facilitar o processamento
            d = d.replace(',', ' ')
            commands = d.split()
            i = 0
            while i < len(commands):
                cmd = commands[i]
                if cmd == 'M':  # Move
                    x = float(commands[i+1])
                    y = float(commands[i+2])
                    ET.SubElement(path, 'move', {'x': str(x), 'y': str(y)})
                    i += 3
                elif cmd == 'L':  # Line
                    x = float(commands[i+1])
                    y = float(commands[i+2])
                    ET.SubElement(path, 'line', {'x': str(x), 'y': str(y)})
                    i += 3
                elif cmd == 'C':  # Curve
                    x1 = float(commands[i+1])
                    y1 = float(commands[i+2])
                    x2 = float(commands[i+3])
                    y2 = float(commands[i+4])
                    x3 = float(commands[i+5])
                    y3 = float(commands[i+6])
                    ET.SubElement(path, 'curve', {
                        'x1': str(x1), 'y1': str(y1),
                        'x2': str(x2), 'y2': str(y2),
                        'x3': str(x3), 'y3': str(y3)
                    })
                    i += 7
                elif cmd == 'Z':  # Close path
                    ET.SubElement(path, 'close')
                    i += 1
                else:
                    i += 1

    # Adiciona fillstroke e stroke (opcional)
    ET.SubElement(foreground, 'fillstroke')
    ET.SubElement(foreground, 'stroke')

    # Salva o shape em um arquivo XML
    tree = ET.ElementTree(shape)
    tree.write(output_file, encoding='utf-8', xml_declaration=True)

    print(f"Shape do Draw.io salvo em: {output_file}")

def main(image_path):
    # Redimensiona a imagem para 78x78 pixels
    resize_image(image_path + '.png', image_path + '_resized.png', (78, 78))
    
    # Converte a imagem PNG para SVG
    image_to_svg(image_path + '_resized.png', image_path + '.svg')

    # Cria o shape para o draw.io
    svg_to_drawio_shape(image_path + '.svg', image_path + '.xml')

    print(f"Shape XML salvo em: {image_path + '.xml'}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python script.py <caminho_da_imagem.png>")
        sys.exit(1)

    image_path = os.path.splitext(sys.argv[1])[0]
    main(image_path)