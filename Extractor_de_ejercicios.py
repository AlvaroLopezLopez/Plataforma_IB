#!/usr/bin/env python3
"""
Procesa todos los .html de la carpeta HTMLS,
extrae los ejercicios y genera, **por cada HTML**:

1) En Ejercicios/Originales/<html_sin_ext>/separados/ejercicio_<n>.json
   — JSON individual por ejercicio.

2) En Ejercicios/Originales/<html_sin_ext>/combinado/exercises.json
   — Un único JSON con el array de todos los ejercicios de ese HTML.

Requisitos:
    pip install beautifulsoup4 markdownify
"""
import os
import re
import json
from bs4 import BeautifulSoup, NavigableString
from markdownify import markdownify as md

def convert_div_to_markdown(div):
    clone = BeautifulSoup(str(div), 'html.parser')

    # 1) Quitar "[Maximum mark: N]"
    for p in clone.find_all('p', string=re.compile(r'^\[Maximum mark:\s*\d+\]$')):
        p.decompose()

    # 2) Procesar KaTeX igual que antes...
    for ann in clone.find_all('annotation', attrs={'encoding':'application/x-tex'}):
        tex = ann.string.strip()
        span = ann.find_parent('span', class_='katex')
        if not span: continue

        if tex.startswith(r'\$'):
            raw = tex[2:]
            raw = re.sub(r'\\hspace\{[^}]*\}', '', raw)
            raw = raw.replace(' ', '')
            repl = NavigableString(f'${raw}$ \\$')
        else:
            content = tex.replace(r'\\\\', '\\')
            repl = NavigableString(f'${content}$')

        span.replace_with(repl)

    # 3) Desenvolver <center>
    for c in clone.find_all('center'):
        c.unwrap()

    # 4) Markdown bruto
    raw_md = md(str(clone), heading_style="ATX")

    # 5) Aplanar párrafos pero conservar listas numeradas
    paras = raw_md.split('\n\n')
    flat = []
    for p in paras:
        lines = [l.rstrip() for l in p.splitlines() if l.strip()]
        if any(re.match(r'^\d+\.\s+', l) for l in lines):
            # es una lista numerada: mantenemos saltos de línea
            flat.append('\n'.join(lines))
        else:
            flat.append(' '.join(lines))
    markdown = '\n\n'.join(flat).strip()

    # 6) Des-escapar subíndices dentro y fuera de math
    markdown = markdown.replace(r'\_', '_')

    return markdown

def process_html_file(html_path, sep_dir):
    """
    Extrae ejercicios de html_path, guarda JSON individuales en sep_dir,
    y devuelve lista con todos los datos de esos ejercicios.
    """
    os.makedirs(sep_dir, exist_ok=True)
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    out = []
    divs = soup.find_all('div', class_='MuiBox-root css-9axr9m')
    for idx, div in enumerate(divs, start=1):
        # Extraer datos meta
        pm = div.find('p', string=re.compile(r'\[Maximum mark:\s*\d+\]'))
        max_mark = int(re.search(r'\d+', pm.text).group()) if pm else None
        calc_tag = div.find_previous(
            lambda t: t.name=='p' and t.get_text(strip=True).lower() in ['calculator','no calculator']
        )
        calculator = (calc_tag.get_text(strip=True).lower()=='calculator') if calc_tag else None
        diff_tag = div.find_previous(
            lambda t: t.name=='p' and t.get_text(strip=True).lower() in ['easy','medium','hard']
        )
        difficulty = diff_tag.get_text(strip=True) if diff_tag else None
        enunciado_md = convert_div_to_markdown(div)

        data = {
            'numero': idx,
            'max_puntacion': max_mark,
            'calculator': calculator,
            'difficulty': difficulty,
            'enunciado_md': enunciado_md
        }
        # Guardar individual
        out_file = os.path.join(sep_dir, f'ejercicio_{idx}.json')
        with open(out_file, 'w', encoding='utf-8') as outf:
            json.dump(data, outf, ensure_ascii=False, indent=2)

        out.append(data)
    return out

def sanitize(name):
    """Convierte un nombre de archivo en identificador válido."""
    base = os.path.splitext(name)[0]
    return re.sub(r'[^\w\-]', '_', base)

def main():
    html_dir     = 'HTMLS'
    originals    = os.path.join('Ejercicios', 'Originales')

    for fname in sorted(os.listdir(html_dir)):
        if not fname.lower().endswith('.html'):
            continue
        src = os.path.join(html_dir, fname)
        folder = sanitize(fname)
        sep_dir = os.path.join(originals, folder, 'separados')
        comb_dir = os.path.join(originals, folder, 'combinado')

        # 1) Generar JSON separados
        ejercicios = process_html_file(src, sep_dir)
        print(f'{fname}: {len(ejercicios)} ejercicios → {sep_dir}')

        # 2) Generar JSON combinado
        os.makedirs(comb_dir, exist_ok=True)
        with open(os.path.join(comb_dir, 'exercises.json'), 'w', encoding='utf-8') as f:
            json.dump(ejercicios, f, ensure_ascii=False, indent=2)
        print(f'   combinado → {comb_dir}/exercises.json')

if __name__ == '__main__':
    main()
