#!/usr/bin/env python3
"""
Script de automação para buscar notícias do mercado de seguros e proteção patrimonial.
Atualiza automaticamente o arquivo src/data/noticias.js com novas notícias.
"""

import os
import json
import re
from datetime import datetime
from openai import OpenAI

# Inicializar cliente OpenAI (API key já configurada via variável de ambiente)
client = OpenAI()

# Palavras-chave para busca de notícias
KEYWORDS = [
    "SUSEP seguros",
    "CNSP seguros",
    "LC 213/2025 proteção patrimonial",
    "Lei 15.040/2024 seguros",
    "mercado seguros Brasil",
    "proteção patrimonial mutualista",
    "associações proteção veicular",
    "CNseg seguros"
]

# Categorias disponíveis
CATEGORIAS = [
    "Lei 15.040/2024",
    "LC 213/2025",
    "Resoluções SUSEP",
    "Resoluções CNSP",
    "Mercado de Seguros",
    "Proteção Patrimonial"
]

def buscar_noticias_recentes():
    """
    Busca notícias recentes usando o modelo GPT para pesquisar e resumir.
    """
    print("🔍 Buscando notícias recentes...")
    
    prompt = f"""Você é um especialista em mercado de seguros e proteção patrimonial no Brasil.

Busque e resuma 3-5 notícias REAIS e RECENTES (últimos 7 dias) sobre os seguintes temas:
- SUSEP (Superintendência de Seguros Privados)
- CNSP (Conselho Nacional de Seguros Privados)
- LC 213/2025 (Lei Complementar sobre proteção patrimonial mutualista)
- Lei 15.040/2024 (Nova Lei de Seguros)
- Mercado de seguros brasileiro
- Proteção patrimonial e proteção veicular
- CNseg (Confederação Nacional das Seguradoras)

Para cada notícia, forneça:
1. Título claro e objetivo
2. Resumo de 1-2 linhas
3. Conteúdo detalhado (3-5 parágrafos)
4. Categoria (escolha uma: {', '.join(CATEGORIAS)})
5. Data (formato YYYY-MM-DD)
6. Fonte oficial
7. 3-5 tags relevantes

IMPORTANTE: 
- Busque apenas notícias REAIS de fontes oficiais
- Priorize notícias dos sites oficiais: SUSEP, CNSP, CNseg
- Data de hoje: {datetime.now().strftime('%Y-%m-%d')}

Retorne no formato JSON:
{{
  "noticias": [
    {{
      "titulo": "...",
      "resumo": "...",
      "conteudo": "...",
      "categoria": "...",
      "data": "YYYY-MM-DD",
      "fonte": "...",
      "tags": ["tag1", "tag2", "tag3"]
    }}
  ]
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Você é um especialista em mercado de seguros brasileiro com acesso a informações atualizadas."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        content = response.choices[0].message.content
        
        # Extrair JSON do conteúdo
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return data.get('noticias', [])
        else:
            print("❌ Erro: Resposta não contém JSON válido")
            return []
            
    except Exception as e:
        print(f"❌ Erro ao buscar notícias: {e}")
        return []

def ler_noticias_existentes():
    """
    Lê as notícias existentes do arquivo noticias.js
    """
    filepath = 'src/data/noticias.js'
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extrair array de notícias
        match = re.search(r'export const noticias = (\[.*?\]);', content, re.DOTALL)
        if match:
            # Converter de JavaScript para JSON válido
            js_array = match.group(1)
            # Remover comentários e trailing commas
            js_array = re.sub(r'//.*?\n', '', js_array)
            js_array = re.sub(r',(\s*[}\]])', r'\1', js_array)
            
            # Tentar parsear
            try:
                noticias = json.loads(js_array)
                return noticias
            except:
                print("⚠️  Erro ao parsear notícias existentes, retornando lista vazia")
                return []
        else:
            return []
            
    except FileNotFoundError:
        print("⚠️  Arquivo noticias.js não encontrado")
        return []

def gerar_id_unico(noticias_existentes):
    """
    Gera um ID único para nova notícia
    """
    if not noticias_existentes:
        return 1
    
    max_id = max([n.get('id', 0) for n in noticias_existentes])
    return max_id + 1

def salvar_noticias(noticias):
    """
    Salva as notícias no arquivo noticias.js
    """
    filepath = 'src/data/noticias.js'
    
    # Converter para formato JavaScript
    js_content = "export const noticias = " + json.dumps(noticias, ensure_ascii=False, indent=2) + ";\n"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print(f"✅ Arquivo {filepath} atualizado com sucesso!")

def main():
    """
    Função principal
    """
    print("=" * 60)
    print("🤖 AUTOMAÇÃO DE NOTÍCIAS - Administradora Mutual")
    print("=" * 60)
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # Buscar novas notícias
    novas_noticias = buscar_noticias_recentes()
    
    if not novas_noticias:
        print("⚠️  Nenhuma notícia nova encontrada")
        return
    
    print(f"✅ Encontradas {len(novas_noticias)} novas notícias")
    
    # Ler notícias existentes
    noticias_existentes = ler_noticias_existentes()
    print(f"📚 Notícias existentes: {len(noticias_existentes)}")
    
    # Adicionar novas notícias no início da lista
    for noticia in novas_noticias:
        noticia['id'] = gerar_id_unico(noticias_existentes)
        noticia['autor'] = "Equipe Administradora Mutual"
        noticia['destaque'] = False  # Primeira notícia será destaque
        
        noticias_existentes.insert(0, noticia)
    
    # Marcar primeira notícia como destaque
    if noticias_existentes:
        noticias_existentes[0]['destaque'] = True
        # Remover destaque das outras
        for n in noticias_existentes[1:]:
            n['destaque'] = False
    
    # Limitar a 50 notícias mais recentes
    noticias_existentes = noticias_existentes[:50]
    
    # Salvar
    salvar_noticias(noticias_existentes)
    
    print()
    print("=" * 60)
    print("✅ AUTOMAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 60)
    
    # Exibir títulos das novas notícias
    print("\n📰 Notícias adicionadas:")
    for i, noticia in enumerate(novas_noticias, 1):
        print(f"  {i}. {noticia['titulo']}")

if __name__ == "__main__":
    main()
