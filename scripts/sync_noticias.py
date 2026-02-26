#!/usr/bin/env python3
"""
Sincroniza os dados de noticias.js para:
1. noticias.json (para consumo dinâmico do frontend)
2. Atualiza o bundle JS compilado (assets/index-*.js) substituindo o array bi
3. Gera a página feed.html formatada

Este script é chamado pelo buscar_noticias.py após atualizar o noticias.js.
"""

import os
import re
import json
import glob
from datetime import datetime

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
NOTICIAS_JS = os.path.join(BASE_DIR, 'src', 'data', 'noticias.js')
NOTICIAS_JSON = os.path.join(BASE_DIR, 'noticias.json')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')


def ler_noticias_js():
    """Lê e parseia o noticias.js para um array Python."""
    with open(NOTICIAS_JS, 'r', encoding='utf-8') as f:
        content = f.read()

    todas_noticias = []

    # 1. Tentar ler a seção dadosNoticias (formato JSON puro)
    dados_match = re.search(r'const dadosNoticias\s*=\s*(\[.*?\]);', content, re.DOTALL)
    if dados_match:
        try:
            dados = json.loads(dados_match.group(1))
            todas_noticias.extend(dados)
            print(f"📄 {len(dados)} notícias lidas de dadosNoticias")
        except json.JSONDecodeError as e:
            print(f"⚠️ Erro ao parsear dadosNoticias: {e}")

    # 2. Tentar ler a seção export const noticias
    match = re.search(r'export const noticias\s*=\s*(\[.*?\]);', content, re.DOTALL)
    if not match and not todas_noticias:
        print("❌ Não encontrou array de notícias")
        return []
    
    if not match:
        return todas_noticias

    js_array = match.group(1)

    # Tentar JSON direto
    try:
        js_noticias = json.loads(js_array)
        todas_noticias.extend(js_noticias)
        return todas_noticias
    except json.JSONDecodeError:
        pass

    # Converter JS para JSON: adicionar aspas nas chaves sem aspas
    js_array = re.sub(r'(?<=[{,\n])\s*(\w+)\s*:', r' "\1":', js_array)

    # Converter aspas simples para duplas
    result = []
    in_double_quote = False
    in_single_quote = False
    in_backtick = False

    i = 0
    while i < len(js_array):
        c = js_array[i]

        if c == '`' and not in_double_quote and not in_single_quote:
            in_backtick = not in_backtick
            result.append('"')
        elif c == '"' and not in_single_quote and not in_backtick:
            in_double_quote = not in_double_quote
            result.append(c)
        elif c == "'" and not in_double_quote and not in_backtick:
            in_single_quote = not in_single_quote
            result.append('"')
        elif c == '\n' and (in_backtick or in_double_quote or in_single_quote):
            result.append('\\n')
        else:
            result.append(c)
        i += 1

    js_array = ''.join(result)

    # Remover trailing commas
    js_array = re.sub(r',(\s*[}\]])', r'\1', js_array)

    # Converter !0 e !1 para true/false
    js_array = js_array.replace(':!0', ':true').replace(':!1', ':false')

    try:
        js_noticias = json.loads(js_array)
        todas_noticias.extend(js_noticias)
        return todas_noticias
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao parsear seção JS do noticias.js: {e}")
        return todas_noticias if todas_noticias else []


def gerar_noticias_json(noticias):
    """Gera o arquivo noticias.json na raiz."""
    with open(NOTICIAS_JSON, 'w', encoding='utf-8') as f:
        json.dump(noticias, f, ensure_ascii=False, indent=2)
    print(f"✅ noticias.json gerado com {len(noticias)} notícias")


def converter_noticia_para_js(noticia):
    """Converte uma notícia Python para formato JS inline (minificado)."""
    parts = []
    
    # Campos obrigatórios
    for key in ['titulo', 'resumo', 'conteudo', 'categoria', 'data', 'fonte', 'fonte_nome', 'autor']:
        val = noticia.get(key, '')
        if val:
            # Escapar aspas duplas e newlines
            val = str(val).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            parts.append(f'{key}:"{val}"')

    # Tags (array de strings)
    tags = noticia.get('tags', [])
    if tags:
        tags_str = ','.join(f'"{t}"' for t in tags)
        parts.append(f'tags:[{tags_str}]')

    # ID (numérico)
    nid = noticia.get('id', 0)
    if isinstance(nid, int):
        parts.append(f'id:{nid}')
    else:
        parts.append(f'id:"{nid}"')

    # Destaque (boolean)
    destaque = noticia.get('destaque', False)
    parts.append(f'destaque:{"!0" if destaque else "!1"}')

    return '{' + ','.join(parts) + '}'


def atualizar_bundle_js(noticias):
    """Atualiza o array bi no bundle JS compilado."""
    # Encontrar o arquivo JS do bundle
    js_files = glob.glob(os.path.join(ASSETS_DIR, 'index-*.js'))
    if not js_files:
        print("❌ Nenhum arquivo JS de bundle encontrado")
        return False

    js_file = js_files[0]
    print(f"📦 Atualizando bundle: {os.path.basename(js_file)}")

    with open(js_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Encontrar o array bi
    start_marker = 'const bi=['
    start = content.find(start_marker)
    if start < 0:
        print("❌ Array bi não encontrado no bundle")
        return False

    # Encontrar o final do array
    pos = start + len('const bi=')
    depth = 0
    end = pos
    for i in range(pos, len(content)):
        if content[i] == '[':
            depth += 1
        elif content[i] == ']':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    # Gerar o novo array
    noticias_js = ','.join(converter_noticia_para_js(n) for n in noticias)
    novo_array = f'const bi=[{noticias_js}]'

    # Substituir no conteúdo
    new_content = content[:start] + novo_array + content[end:]

    with open(js_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"✅ Bundle atualizado: {len(noticias)} notícias injetadas")
    return True


def main():
    print("🔄 Sincronizando dados de notícias...")
    
    noticias = ler_noticias_js()
    if not noticias:
        print("❌ Nenhuma notícia encontrada para sincronizar")
        return

    print(f"📰 {len(noticias)} notícias carregadas do noticias.js")

    # 1. Gerar noticias.json
    gerar_noticias_json(noticias)

    # 2. Atualizar bundle JS
    atualizar_bundle_js(noticias)

    print("✅ Sincronização concluída!")


if __name__ == "__main__":
    main()
