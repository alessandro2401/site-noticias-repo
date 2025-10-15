#!/usr/bin/env python3
"""
Script de automação para buscar notícias usando Perplexity API.
Atualiza automaticamente o arquivo src/data/noticias.js com novas notícias.
"""

import os
import json
import re
import requests
from datetime import datetime

# API Key do Perplexity
SONAR_API_KEY = os.environ.get('SONAR_API_KEY')

# Categorias disponíveis
CATEGORIAS = [
    "Lei 15.040/2024",
    "LC 213/2025",
    "Resoluções SUSEP",
    "Resoluções CNSP",
    "Mercado de Seguros",
    "Proteção Patrimonial"
]

def buscar_noticias_perplexity():
    """
    Busca notícias recentes usando Perplexity API.
    """
    print("🔍 Buscando notícias recentes com Perplexity...")
    
    prompt = """Você é um especialista em mercado de seguros e proteção patrimonial no Brasil.

Busque e resuma 5 notícias REAIS e RECENTES (últimos 7 dias) sobre os seguintes temas:
- SUSEP (Superintendência de Seguros Privados)
- CNSP (Conselho Nacional de Seguros Privados)
- LC 213/2025 (Lei Complementar sobre proteção patrimonial mutualista)
- Lei 15.040/2024 (Nova Lei de Seguros)
- CNseg (Confederação Nacional das Seguradoras)
- Mercado de seguros brasileiro
- Proteção patrimonial mutualista

Para cada notícia, forneça:
1. Título claro e objetivo
2. Resumo de 1-2 frases
3. Data (formato DD/MM/AAAA)
4. Categoria (escolha entre: Lei 15.040/2024, LC 213/2025, Resoluções SUSEP, Resoluções CNSP, Mercado de Seguros, Proteção Patrimonial)
5. Tags relevantes (2-3 palavras-chave)

Formato de resposta (JSON):
```json
[
  {
    "titulo": "Título da notícia",
    "resumo": "Resumo breve da notícia",
    "data": "DD/MM/AAAA",
    "categoria": "Categoria",
    "tags": ["tag1", "tag2", "tag3"]
  }
]
```

Retorne APENAS o JSON, sem texto adicional."""

    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {SONAR_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "sonar-pro",
                "messages": [
                    {
                        "role": "system",
                        "content": "Você é um assistente especializado em buscar notícias recentes e reais do mercado de seguros brasileiro."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 2000
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Extrair JSON do conteúdo
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                noticias_json = json_match.group(1)
            else:
                # Tentar encontrar array JSON diretamente
                json_match = re.search(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)
                if json_match:
                    noticias_json = json_match.group(0)
                else:
                    print("⚠️  Não foi possível extrair JSON da resposta")
                    return []
            
            noticias = json.loads(noticias_json)
            print(f"✅ {len(noticias)} notícias encontradas")
            return noticias
        else:
            print(f"❌ Erro na API: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Erro ao buscar notícias: {e}")
        return []

def formatar_noticias_js(noticias):
    """
    Formata as notícias no formato JavaScript para o arquivo noticias.js
    """
    js_noticias = []
    
    for i, noticia in enumerate(noticias, 1):
        # Gerar ID único baseado no título
        slug = re.sub(r'[^a-z0-9]+', '-', noticia['titulo'].lower()).strip('-')
        id_noticia = f"{slug[:50]}"
        
        js_noticia = f"""  {{
    id: '{id_noticia}',
    titulo: '{noticia['titulo']}',
    resumo: '{noticia['resumo']}',
    data: '{noticia['data']}',
    categoria: '{noticia['categoria']}',
    tags: {json.dumps(noticia['tags'], ensure_ascii=False)}
  }}"""
        
        js_noticias.append(js_noticia)
    
    return ",\n".join(js_noticias)

def atualizar_arquivo_noticias(noticias):
    """
    Atualiza o arquivo src/data/noticias.js com as novas notícias
    """
    arquivo_path = 'src/data/noticias.js'
    
    try:
        # Ler arquivo atual
        with open(arquivo_path, 'r', encoding='utf-8') as f:
            conteudo_atual = f.read()
        
        # Extrair notícias existentes
        match = re.search(r'export const noticias = \[(.*?)\];', conteudo_atual, re.DOTALL)
        if match:
            noticias_existentes_str = match.group(1).strip()
        else:
            noticias_existentes_str = ""
        
        # Formatar novas notícias
        novas_noticias_str = formatar_noticias_js(noticias)
        
        # Combinar (novas notícias primeiro)
        if noticias_existentes_str:
            todas_noticias_str = f"{novas_noticias_str},\n{noticias_existentes_str}"
        else:
            todas_noticias_str = novas_noticias_str
        
        # Criar novo conteúdo
        novo_conteudo = f"""// Notícias do mercado de seguros e proteção patrimonial
// Atualizado automaticamente em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

export const noticias = [
{todas_noticias_str}
];
"""
        
        # Escrever arquivo
        with open(arquivo_path, 'w', encoding='utf-8') as f:
            f.write(novo_conteudo)
        
        print(f"✅ Arquivo {arquivo_path} atualizado com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar arquivo: {e}")
        return False

def main():
    print("=" * 60)
    print("🤖 AUTOMAÇÃO DE NOTÍCIAS - Administradora Mutual")
    print("=" * 60)
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # Buscar notícias
    noticias = buscar_noticias_perplexity()
    
    if not noticias:
        print("⚠️  Nenhuma notícia nova encontrada")
        return
    
    # Atualizar arquivo
    if atualizar_arquivo_noticias(noticias):
        print()
        print("=" * 60)
        print("✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 60)
        print(f"📰 {len(noticias)} notícias adicionadas")
        print()
        print("📝 Próximos passos:")
        print("   1. Revisar as notícias em src/data/noticias.js")
        print("   2. Fazer commit das alterações")
        print("   3. Fazer push para o repositório")
        print("   4. Aguardar deploy automático no Vercel")
    else:
        print("❌ Falha na atualização")

if __name__ == "__main__":
    main()

