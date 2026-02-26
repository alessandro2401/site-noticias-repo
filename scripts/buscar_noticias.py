#!/usr/bin/env python3
"""
Mutual News Hub — Agregador Inteligente de Notícias
Script de automação para buscar notícias do mercado de seguros e proteção patrimonial
a partir dos principais portais de notícias do Brasil.

Fluxo:
1. Acessa os portais de notícias listados
2. Coleta links de artigos recentes
3. Filtra por palavras-chave relevantes ao setor
4. Processa com IA (OpenAI) para gerar resumos e categorizar
5. Atualiza o arquivo src/data/noticias.js
6. Gera o feed RSS em rss.xml

Autor: Manus AI para Administradora Mutual
Data: 25/02/2026
"""

import os
import json
import re
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_SCRAPING = True
except ImportError:
    HAS_SCRAPING = False
    print("⚠️  requests/beautifulsoup4 não disponíveis. Usando modo IA puro.")

from openai import OpenAI

# ============================================================
# CONFIGURAÇÃO
# ============================================================

client = OpenAI()

# Palavras-chave para filtragem de relevância (case-insensitive)
KEYWORDS_RELEVANCIA = [
    "seguro", "seguros", "seguradora", "seguradoras",
    "susep", "cnsp", "cnseg", "fenseg", "fenaprevi", "fenacor",
    "mutualista", "mutualismo", "mutual",
    "proteção patrimonial", "proteção veicular",
    "lei 15.040", "lei 15040", "lc 213",
    "sinistro", "apólice", "prêmio de seguro",
    "resseguro", "corretora de seguros", "corretor de seguros",
    "mercado segurador", "setor segurador",
    "proteção coletiva", "associação de proteção",
]

# Categorias do site
CATEGORIAS = [
    "Lei 15.040/2024",
    "LC 213/2025",
    "Resoluções SUSEP",
    "Resoluções CNSP",
    "Mercado de Seguros",
    "Proteção Patrimonial"
]

# ============================================================
# FONTES DE NOTÍCIAS — Portais Monitorados
# ============================================================

FONTES_NACIONAIS = [
    {"nome": "G1", "url": "https://g1.globo.com/economia/", "dominio": "g1.globo.com"},
    {"nome": "Folha de S. Paulo", "url": "https://www1.folha.uol.com.br/mercado/", "dominio": "folha.uol.com.br"},
    {"nome": "Estadão", "url": "https://www.estadao.com.br/economia/", "dominio": "estadao.com.br"},
    {"nome": "CNN Brasil", "url": "https://www.cnnbrasil.com.br/economia/", "dominio": "cnnbrasil.com.br"},
    {"nome": "UOL Economia", "url": "https://economia.uol.com.br/", "dominio": "uol.com.br"},
    {"nome": "Valor Econômico", "url": "https://valor.globo.com/financas/", "dominio": "valor.globo.com"},
    {"nome": "Exame", "url": "https://exame.com/economia/", "dominio": "exame.com"},
    {"nome": "Metrópoles", "url": "https://www.metropoles.com/negocios/", "dominio": "metropoles.com"},
    {"nome": "R7", "url": "https://noticias.r7.com/economia/", "dominio": "r7.com"},
    {"nome": "Veja", "url": "https://veja.abril.com.br/economia/", "dominio": "veja.abril.com.br"},
    {"nome": "Gazeta do Povo", "url": "https://www.gazetadopovo.com.br/economia/", "dominio": "gazetadopovo.com.br"},
    {"nome": "Poder360", "url": "https://www.poder360.com.br/economia/", "dominio": "poder360.com.br"},
    {"nome": "Agência Brasil", "url": "https://agenciabrasil.ebc.com.br/economia", "dominio": "agenciabrasil.ebc.com.br"},
    {"nome": "Correio Braziliense", "url": "https://www.correiobraziliense.com.br/economia/", "dominio": "correiobraziliense.com.br"},
    {"nome": "Terra", "url": "https://www.terra.com.br/economia/", "dominio": "terra.com.br"},
]

FONTES_SETOR = [
    {"nome": "SUSEP", "url": "https://www.gov.br/susep/pt-br/assuntos/noticias", "dominio": "gov.br/susep"},
    {"nome": "CNseg", "url": "https://cnseg.org.br/noticias/", "dominio": "cnseg.org.br"},
    {"nome": "Sincor-SP", "url": "https://www.sincor.org.br/noticias/", "dominio": "sincor.org.br"},
    {"nome": "CQCS", "url": "https://cqcs.com.br/", "dominio": "cqcs.com.br"},
    {"nome": "Sonho Seguro", "url": "https://www.sonhoseguro.com.br/", "dominio": "sonhoseguro.com.br"},
    {"nome": "Revista Apólice", "url": "https://www.revistaapolice.com.br/", "dominio": "revistaapolice.com.br"},
]

FONTES_GOIAS = [
    {"nome": "O Popular", "url": "https://opopular.com.br/", "dominio": "opopular.com.br"},
    {"nome": "Jornal Opção", "url": "https://www.jornalopcao.com.br/", "dominio": "jornalopcao.com.br"},
    {"nome": "Portal 6", "url": "https://portal6.com.br/", "dominio": "portal6.com.br"},
    {"nome": "Mais Goiás", "url": "https://www.maisgoias.com.br/", "dominio": "maisgoias.com.br"},
]

TODAS_FONTES = FONTES_SETOR + FONTES_NACIONAIS + FONTES_GOIAS

# Arquivo para rastrear URLs já processadas
PROCESSED_URLS_FILE = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'processed_urls.json')
NOTICIAS_FILE = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'noticias.js')
RSS_FILE = os.path.join(os.path.dirname(__file__), '..', 'rss.xml')


# ============================================================
# FUNÇÕES DE SCRAPING
# ============================================================

def carregar_urls_processadas():
    """Carrega o registro de URLs já processadas."""
    try:
        with open(PROCESSED_URLS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def salvar_urls_processadas(urls):
    """Salva o registro de URLs processadas. Mantém apenas as últimas 500."""
    urls = urls[-500:]
    os.makedirs(os.path.dirname(PROCESSED_URLS_FILE), exist_ok=True)
    with open(PROCESSED_URLS_FILE, 'w', encoding='utf-8') as f:
        json.dump(urls, f, ensure_ascii=False, indent=2)


def gerar_hash_url(url):
    """Gera um hash curto para identificar uma URL."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def extrair_links_artigos(fonte):
    """
    Acessa a página principal de um portal de notícias e extrai
    os links dos artigos mais recentes.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    }

    try:
        response = requests.get(fonte['url'], headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')

        links = set()
        base_url = fonte['url']

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(base_url, href)

            # Filtrar apenas links do mesmo domínio
            parsed = urlparse(full_url)
            if fonte['dominio'] not in parsed.netloc:
                continue

            # Filtrar links que parecem ser artigos (URLs longas com segmentos)
            path = parsed.path.strip('/')
            if len(path.split('/')) < 2:
                continue

            # Ignorar links de categorias, tags, autores, páginas genéricas
            ignore_patterns = [
                '/tag/', '/tags/', '/autor/', '/author/', '/page/',
                '/categoria/', '/category/', '/login', '/cadastro',
                '/assine', '/newsletter', '/sobre', '/contato',
                '.jpg', '.png', '.gif', '.pdf', '.mp4',
            ]
            if any(p in full_url.lower() for p in ignore_patterns):
                continue

            links.add(full_url)

        print(f"  📎 {fonte['nome']}: {len(links)} links encontrados")
        return list(links)[:20]  # Limitar a 20 links por fonte

    except Exception as e:
        print(f"  ❌ {fonte['nome']}: Erro ao acessar - {str(e)[:80]}")
        return []


def extrair_texto_artigo(url):
    """
    Acessa um artigo e extrai o texto principal.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    }

    try:
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')

        # Remover elementos indesejados
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
            tag.decompose()

        # Tentar extrair o título
        titulo = ''
        for selector in ['h1', 'article h1', '.post-title', '.entry-title', '.article-title']:
            el = soup.select_one(selector)
            if el:
                titulo = el.get_text(strip=True)
                break

        # Tentar extrair o conteúdo do artigo
        texto = ''
        for selector in ['article', '.post-content', '.entry-content', '.article-body',
                          '.content-text', '.materia-conteudo', '.text', '[itemprop="articleBody"]',
                          '.mc-body', '.content-publication-body']:
            el = soup.select_one(selector)
            if el:
                paragrafos = el.find_all('p')
                texto = '\n'.join(p.get_text(strip=True) for p in paragrafos if len(p.get_text(strip=True)) > 30)
                if len(texto) > 200:
                    break

        # Fallback: pegar todos os parágrafos da página
        if len(texto) < 200:
            paragrafos = soup.find_all('p')
            texto = '\n'.join(p.get_text(strip=True) for p in paragrafos if len(p.get_text(strip=True)) > 30)

        return titulo, texto[:5000]  # Limitar a 5000 caracteres

    except Exception as e:
        return '', ''


def filtrar_por_relevancia(titulo, texto):
    """
    Verifica se o artigo é relevante para o mercado de seguros
    e proteção patrimonial, baseado em palavras-chave.
    """
    conteudo = (titulo + ' ' + texto).lower()
    for keyword in KEYWORDS_RELEVANCIA:
        if keyword.lower() in conteudo:
            return True
    return False


# ============================================================
# FUNÇÕES DE PROCESSAMENTO COM IA
# ============================================================

def processar_artigos_com_ia(artigos_brutos):
    """
    Envia os artigos coletados para a OpenAI para gerar resumos,
    categorizar e extrair tags.
    """
    if not artigos_brutos:
        return []

    # Preparar o conteúdo para envio
    artigos_texto = ""
    for i, artigo in enumerate(artigos_brutos, 1):
        artigos_texto += f"\n--- ARTIGO {i} ---\n"
        artigos_texto += f"FONTE: {artigo['fonte_nome']}\n"
        artigos_texto += f"URL: {artigo['url']}\n"
        artigos_texto += f"TÍTULO ORIGINAL: {artigo['titulo']}\n"
        artigos_texto += f"TEXTO: {artigo['texto'][:2000]}\n"

    prompt = f"""Você é um especialista em mercado de seguros e proteção patrimonial no Brasil.

Analise os artigos abaixo e, para cada um que seja RELEVANTE para o setor de seguros, proteção patrimonial mutualista ou regulamentação (SUSEP, CNSP, etc.), gere uma notícia formatada.

CATEGORIAS DISPONÍVEIS: {', '.join(CATEGORIAS)}

Para cada artigo relevante, retorne:
1. titulo: Título claro e objetivo (pode ser o original ou reescrito)
2. resumo: Resumo de 1-2 frases
3. conteudo: Texto detalhado de 3-5 parágrafos explicando a notícia
4. categoria: Uma das categorias listadas acima
5. data: Data no formato YYYY-MM-DD (use a data de hoje {datetime.now().strftime('%Y-%m-%d')} se não identificar)
6. fonte: URL original do artigo
7. fonte_nome: Nome do portal de origem
8. tags: 3-5 tags relevantes

IMPORTANTE:
- Descarte artigos que NÃO sejam sobre seguros, proteção patrimonial ou regulamentação do setor
- Não invente informações; baseie-se apenas no conteúdo fornecido
- Se um artigo não tiver informação suficiente, descarte-o

Retorne APENAS um JSON válido no formato:
{{
  "noticias": [
    {{
      "titulo": "...",
      "resumo": "...",
      "conteudo": "...",
      "categoria": "...",
      "data": "YYYY-MM-DD",
      "fonte": "https://...",
      "fonte_nome": "Nome do Portal",
      "tags": ["tag1", "tag2", "tag3"]
    }}
  ]
}}

ARTIGOS PARA ANÁLISE:
{artigos_texto}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Você é um especialista em mercado de seguros brasileiro. Retorne apenas JSON válido, sem texto adicional."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4000
        )

        content = response.choices[0].message.content

        # Extrair JSON
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            noticias = data.get('noticias', [])
            print(f"  ✅ IA processou e retornou {len(noticias)} notícias relevantes")
            return noticias
        else:
            print("  ⚠️  Resposta da IA não contém JSON válido")
            return []

    except Exception as e:
        print(f"  ❌ Erro ao processar com IA: {e}")
        return []


def buscar_noticias_modo_ia_puro():
    """
    Modo alternativo: usa a IA diretamente para buscar notícias
    quando o scraping não está disponível.
    """
    print("🤖 Usando modo IA puro (sem scraping)...")

    fontes_lista = "\n".join([f"- {f['nome']} ({f['url']})" for f in TODAS_FONTES])

    prompt = f"""Você é um especialista em mercado de seguros e proteção patrimonial no Brasil.

Busque e resuma 5-8 notícias REAIS e RECENTES (últimos 7 dias) sobre os seguintes temas:
- SUSEP (Superintendência de Seguros Privados)
- CNSP (Conselho Nacional de Seguros Privados)
- LC 213/2025 (Lei Complementar sobre proteção patrimonial mutualista)
- Lei 15.040/2024 (Nova Lei de Seguros)
- Mercado de seguros brasileiro
- Proteção patrimonial e proteção veicular
- CNseg (Confederação Nacional das Seguradoras)

Priorize notícias dos seguintes portais:
{fontes_lista}

Para cada notícia, forneça:
1. titulo: Título claro e objetivo
2. resumo: Resumo de 1-2 linhas
3. conteudo: Conteúdo detalhado (3-5 parágrafos)
4. categoria: Escolha uma: {', '.join(CATEGORIAS)}
5. data: Formato YYYY-MM-DD
6. fonte: URL da fonte oficial
7. fonte_nome: Nome do portal de origem
8. tags: 3-5 tags relevantes

Data de hoje: {datetime.now().strftime('%Y-%m-%d')}

Retorne APENAS JSON válido:
{{
  "noticias": [
    {{
      "titulo": "...",
      "resumo": "...",
      "conteudo": "...",
      "categoria": "...",
      "data": "YYYY-MM-DD",
      "fonte": "https://...",
      "fonte_nome": "Nome do Portal",
      "tags": ["tag1", "tag2", "tag3"]
    }}
  ]
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Você é um especialista em mercado de seguros brasileiro com acesso a informações atualizadas. Retorne apenas JSON válido."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=4000
        )

        content = response.choices[0].message.content
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return data.get('noticias', [])
        return []

    except Exception as e:
        print(f"❌ Erro no modo IA puro: {e}")
        return []


# ============================================================
# FUNÇÕES DE PERSISTÊNCIA
# ============================================================

def ler_noticias_existentes():
    """Lê as notícias existentes do arquivo noticias.js"""
    try:
        with open(NOTICIAS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()

        match = re.search(r'export const noticias = (\[.*?\]);', content, re.DOTALL)
        if match:
            js_array = match.group(1)
            js_array = re.sub(r'//.*?\n', '', js_array)
            js_array = re.sub(r',(\s*[}\]])', r'\1', js_array)
            try:
                return json.loads(js_array)
            except:
                print("⚠️  Erro ao parsear notícias existentes")
                return []
        return []
    except FileNotFoundError:
        return []


def salvar_noticias(noticias):
    """Salva as notícias no arquivo noticias.js"""
    os.makedirs(os.path.dirname(NOTICIAS_FILE), exist_ok=True)
    js_content = "export const noticias = " + json.dumps(noticias, ensure_ascii=False, indent=2) + ";\n"
    with open(NOTICIAS_FILE, 'w', encoding='utf-8') as f:
        f.write(js_content)
    print(f"✅ Arquivo noticias.js atualizado com sucesso!")


def gerar_id_unico(noticias_existentes):
    """Gera um ID numérico único para nova notícia."""
    if not noticias_existentes:
        return 1
    ids_numericos = [n.get('id', 0) for n in noticias_existentes if isinstance(n.get('id'), int)]
    return max(ids_numericos, default=0) + 1


# ============================================================
# GERADOR DE RSS
# ============================================================

def gerar_rss(noticias):
    """Gera o arquivo rss.xml com as notícias mais recentes."""
    site_url = "https://noticias.administradoramutual.com.br"
    agora = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')

    items_xml = ""
    for noticia in noticias[:30]:  # Últimas 30 notícias no feed
        titulo = noticia.get('titulo', 'Sem título')
        resumo = noticia.get('resumo', '')
        data_str = noticia.get('data', '')
        fonte = noticia.get('fonte', '')
        fonte_nome = noticia.get('fonte_nome', '')
        nid = noticia.get('id', '')
        categoria = noticia.get('categoria', '')

        # Formatar data para RSS (RFC 822)
        try:
            if '-' in str(data_str):
                dt = datetime.strptime(str(data_str), '%Y-%m-%d')
            elif '/' in str(data_str):
                dt = datetime.strptime(str(data_str), '%d/%m/%Y')
            else:
                dt = datetime.now()
            pub_date = dt.strftime('%a, %d %b %Y 08:00:00 -0300')
        except:
            pub_date = agora

        # Escapar caracteres especiais para XML
        titulo_xml = titulo.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        resumo_xml = resumo.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        fonte_info = f" (Fonte: {fonte_nome})" if fonte_nome else ""

        items_xml += f"""    <item>
      <title>{titulo_xml}</title>
      <link>{site_url}/#/noticia/{nid}</link>
      <description>{resumo_xml}{fonte_info}</description>
      <pubDate>{pub_date}</pubDate>
      <category>{categoria}</category>
      <guid isPermaLink="false">{nid}</guid>
    </item>
"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Notícias - Administradora Mutual</title>
    <link>{site_url}</link>
    <description>Central de notícias sobre mercado de seguros, proteção patrimonial mutualista, regulamentações da SUSEP e CNSP</description>
    <language>pt-BR</language>
    <lastBuildDate>{agora}</lastBuildDate>
    <atom:link href="{site_url}/rss.xml" rel="self" type="application/rss+xml"/>
    <image>
      <url>{site_url}/favicon-192.png</url>
      <title>Administradora Mutual</title>
      <link>{site_url}</link>
    </image>
{items_xml}  </channel>
</rss>
"""

    with open(RSS_FILE, 'w', encoding='utf-8') as f:
        f.write(rss_xml)
    print(f"✅ Feed RSS gerado em rss.xml ({len(noticias[:30])} itens)")


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def main():
    print("=" * 60)
    print("📰 MUTUAL NEWS HUB — Agregador de Notícias")
    print("   Administradora Mutual")
    print("=" * 60)
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()

    novas_noticias = []

    # ---- MODO 1: Scraping + IA ----
    if HAS_SCRAPING:
        print("🌐 Modo: Scraping + IA (coletando de portais reais)")
        print("-" * 40)

        urls_processadas = carregar_urls_processadas()
        artigos_brutos = []

        # Iterar por todas as fontes
        for fonte in TODAS_FONTES:
            print(f"\n🔍 Monitorando: {fonte['nome']} ({fonte['url'][:50]}...)")

            links = extrair_links_artigos(fonte)

            # Filtrar links já processados
            links_novos = [l for l in links if gerar_hash_url(l) not in urls_processadas]
            if not links_novos:
                print(f"  ℹ️  Nenhum link novo encontrado")
                continue

            print(f"  🆕 {len(links_novos)} links novos para analisar")

            # Extrair texto dos artigos e filtrar por relevância
            for url in links_novos[:5]:  # Máximo 5 artigos por fonte
                titulo, texto = extrair_texto_artigo(url)
                if not texto or len(texto) < 100:
                    continue

                if filtrar_por_relevancia(titulo, texto):
                    artigos_brutos.append({
                        'url': url,
                        'titulo': titulo,
                        'texto': texto,
                        'fonte_nome': fonte['nome'],
                        'fonte_url': fonte['url'],
                    })
                    urls_processadas.append(gerar_hash_url(url))
                    print(f"    ✅ Relevante: {titulo[:60]}...")

        print(f"\n📊 Total de artigos relevantes coletados: {len(artigos_brutos)}")

        # Processar com IA em lotes de até 8 artigos
        if artigos_brutos:
            for i in range(0, len(artigos_brutos), 8):
                lote = artigos_brutos[i:i+8]
                print(f"\n🤖 Processando lote {i//8 + 1} com {len(lote)} artigos...")
                noticias_lote = processar_artigos_com_ia(lote)
                novas_noticias.extend(noticias_lote)

        # Salvar URLs processadas
        salvar_urls_processadas(urls_processadas)

    # ---- MODO 2: IA Pura (fallback) ----
    if not novas_noticias:
        print("\n🤖 Complementando com busca via IA pura...")
        novas_noticias = buscar_noticias_modo_ia_puro()

    # ---- CONSOLIDAR E SALVAR ----
    if not novas_noticias:
        print("\n⚠️  Nenhuma notícia nova encontrada nesta execução")
        return

    print(f"\n📰 Total de novas notícias: {len(novas_noticias)}")

    # Ler notícias existentes
    noticias_existentes = ler_noticias_existentes()
    print(f"📚 Notícias existentes: {len(noticias_existentes)}")

    # Adicionar novas notícias no início
    for noticia in novas_noticias:
        noticia['id'] = gerar_id_unico(noticias_existentes)
        noticia['autor'] = "Equipe Administradora Mutual"
        noticia['destaque'] = False

        # Garantir que fonte_nome existe (compatibilidade)
        if 'fonte_nome' not in noticia:
            noticia['fonte_nome'] = ''

        noticias_existentes.insert(0, noticia)

    # Marcar primeira notícia como destaque
    if noticias_existentes:
        noticias_existentes[0]['destaque'] = True
        for n in noticias_existentes[1:]:
            n['destaque'] = False

    # Limitar a 100 notícias mais recentes
    noticias_existentes = noticias_existentes[:100]

    # Salvar notícias
    salvar_noticias(noticias_existentes)

    # Gerar RSS
    gerar_rss(noticias_existentes)

    # Sincronizar dados: atualizar noticias.json e bundle JS
    print("\n🔄 Sincronizando dados para o frontend...")
    try:
        from sync_noticias import main as sync_main
        sync_main()
    except Exception as e:
        print(f"⚠️  Erro na sincronização: {e}")
        # Fallback: tentar importar do diretório correto
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("sync_noticias", os.path.join(os.path.dirname(__file__), 'sync_noticias.py'))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.main()
        except Exception as e2:
            print(f"❌ Falha na sincronização: {e2}")

    print()
    print("=" * 60)
    print("✅ MUTUAL NEWS HUB — ATUALIZAÇÃO CONCLUÍDA!")
    print("=" * 60)
    print(f"\n📰 Notícias adicionadas ({len(novas_noticias)}):")
    for i, n in enumerate(novas_noticias, 1):
        fonte_info = f" [{n.get('fonte_nome', '')}]" if n.get('fonte_nome') else ""
        print(f"  {i}. {n['titulo']}{fonte_info}")


if __name__ == "__main__":
    main()
