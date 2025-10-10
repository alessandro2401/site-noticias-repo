#!/usr/bin/env python3
"""
API Serverless do Vercel para buscar notícias automaticamente.
Esta função é chamada pelo Vercel Cron Job diariamente às 11h.
"""

from http.server import BaseHTTPRequestHandler
import os
import json
import re
import subprocess
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """
        Handler para requisições GET.
        Executa o script de busca de notícias e retorna o resultado.
        """
        try:
            # Verificar se a requisição tem o token de autorização correto
            auth_header = self.headers.get('Authorization')
            expected_token = os.environ.get('CRON_SECRET', 'default-secret')
            
            if auth_header != f'Bearer {expected_token}':
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'Unauthorized',
                    'message': 'Token de autorização inválido'
                }).encode())
                return
            
            # Executar o script de busca de notícias
            script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'buscar_noticias.py')
            
            # Executar o script
            result = subprocess.run(
                ['python3', script_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos de timeout
            )
            
            # Preparar resposta
            if result.returncode == 0:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                response = {
                    'success': True,
                    'message': 'Notícias atualizadas com sucesso!',
                    'timestamp': datetime.now().isoformat(),
                    'output': result.stdout
                }
                
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            else:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                response = {
                    'success': False,
                    'message': 'Erro ao executar script de busca de notícias',
                    'error': result.stderr,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                'success': False,
                'message': 'Erro interno do servidor',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))

