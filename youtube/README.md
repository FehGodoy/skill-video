# Upload no YouTube (sempre privado)

Os vídeos sobem como **privados**. Você revisa no YouTube Studio e publica ou agenda.

## Configuração (uma vez só)

1. Em https://console.cloud.google.com crie um projeto (ex.: `skill-video`).
2. **APIs e serviços → Biblioteca →** ative a **YouTube Data API v3**.
3. **Tela de consentimento OAuth:** tipo *Externo*, adicione o seu e-mail como **usuário de teste**.
4. **Credenciais → Criar credenciais → ID do cliente OAuth → App para computador.**
5. Baixe o JSON e salve como `youtube/client_secret.json`. Ele **nunca vai para o git**.
6. Instale as dependências:
   ```
   pip install -r youtube/requirements.txt
   ```
7. Autorize cada canal. Abre o navegador; escolha o canal certo na tela de seleção:
   ```
   python youtube/upload.py auth --canal honda
   python youtube/upload.py auth --canal gesund
   ```

Os tokens ficam em `youtube/tokens/`, um por canal, também fora do git.

## Enviar um vídeo

```
python youtube/upload.py upload --canal honda --video honda-teste/honda_teste.mp4 --titulo "Honda Legends in 40 Seconds" --tags "honda,civic,nsx"
```

O vídeo é marcado como conteúdo sintético (IA) e não destinado a crianças.

## Limites

- **Cota:** ~6 uploads por dia por projeto do Google Cloud (10.000 unidades; cada upload custa 1.600).
- **App em modo de teste:** o token de autorização expira em 7 dias, e aí é preciso rodar `auth` de novo. Publicar a tela de consentimento resolve isso.
