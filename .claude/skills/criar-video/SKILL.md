---
name: criar-video
description: Cria um vídeo completo de 8–10 min no estilo "colagem explicativa" para o canal Honda Deep Dive (inglês) ou Gesund ab 60 (alemão) — escolhe o tema, escreve o roteiro, narra com Cartesia, gera imagens realistas no Kaggle (GPU grátis), monta o vídeo com legendas, escreve prompts de thumbnail e envia ao YouTube como PRIVADO. Use quando o usuário pedir "cria um vídeo", "novo vídeo pro canal X", "faz um vídeo sobre Y".
---

# Criar vídeo (estilo colagem explicativa)

Projeto: `D:\Projetos\skill-video`. Configuração dos canais em `canais.json`
(voz, idioma, velocidade, estilo de imagem, público, exemplos de títulos, cuidados).
Leia `canais.json` antes de começar.

## 1. Entender o pedido
- **Canal** (`honda` ou `gesund`): obrigatório. Se não estiver claro, pergunte.
- **Tema**: se o usuário não der, proponha 3 temas no estilo dos `estilo_titulos`
  do canal (curiosidade, lista, medo de errar, dinheiro/saúde) e deixe ele escolher.
  Pode pesquisar na web tendências do nicho para embasar.
- **Enviar ao YouTube?** Padrão: sim, como privado. Pergunte só se houver dúvida.

## 2. Escrever o roteiro
Crie `videos/<slug>/roteiro.json` (slug curto, minúsculo, com hífens). Formato:

```json
{
 "canal": "honda",
 "voice_id": "<de canais.json>",
 "language": "en",
 "velocidade": 0.9,
 "titulo": "Título no estilo do canal (máx. 100 caracteres)",
 "descricao": "2–3 frases + aviso de imagens geradas por IA (+ aviso médico no gesund)",
 "tags": "tag1,tag2,...",
 "estilo_imagem": "<de canais.json>",
 "cenas": [
  {"titulo": "Título curto da tela",
   "falas": [
    {"texto": "Frase falada, com a *palavra-chave* entre asteriscos.",
     "imagens": [{"id": "h001", "prompt": "cena em inglês, concreta, sem texto", "rotulo": "Rótulo curto"}]},
    {"texto": "Outra frase.", "topicos": ["Item 1", "Item 2", "Item 3"]}
   ]}
 ]
}
```

Regras do roteiro:
- **Duração**: 8–10 min ⇒ ~1.400–1.700 palavras (inglês) ou ~1.200–1.400 (alemão).
  12–17 cenas, 4–6 falas por cena.
- Estrutura: gancho forte (promessa + "fique até o fim") → itens da lista
  (uma cena cada) → dicas práticas → resumo → pedido de comentário e inscrição.
- **Imagens**: ~1 a cada 1–2 falas (60–80 por vídeo). IDs únicos com prefixo do
  canal (`h001`… / `g001`…). Prompt em inglês, descrevendo uma foto concreta;
  nada de texto na imagem; carros com "no logos". Rótulo curto no idioma do vídeo.
- **Tópicos**: listas curtas (2–4 itens de até ~25 caracteres).
- Marque 1 palavra-chave por fala com `*asteriscos*` (vira vermelho na legenda).
- Siga os `cuidados` do canal. No **gesund**: aviso "ersetzt keinen Arztbesuch"
  na primeira cena, 112 para sintomas de emergência, nunca mandar parar remédio,
  só informação médica consensual.
- Conte as palavras e ajuste antes de seguir.

## 3. Gerar e montar
Rode em background (leva ~40–50 min, quase tudo no Kaggle):

```bash
python -u motor/gerar_video.py videos/<slug> --enviar
```

Etapas (cada uma é pulada se já estiver pronta):
1. `motor/narrar.py` — Cartesia via WebSocket, com tempo de cada palavra.
   Mostra a duração total; se ficar abaixo de 8 min, alongue o roteiro, apague
   `narracao.json` e rode de novo.
2. `motor/imagens_kaggle.py` — envia o notebook pela API do Kaggle
   (`KAGGLE_API_TOKEN` no `.env`), espera e baixa as imagens (~15 s cada).
3. `motor/montar.py` — fundo claro, título da cena, imagens surgindo com rótulos,
   tópicos e legendas sincronizadas → `video.mp4`.
4. `youtube/upload.py` — envia como **privado** no canal certo (token por canal
   em `youtube/tokens/`), com conteúdo sintético marcado e `thumb.png` se existir.

Antes do envio, confira 3–4 quadros do vídeo (extraia com ffmpeg e olhe) e uma
folha de contato das imagens (logos, deformações, texto estranho). Se algo
estiver errado, corrija e refaça só a etapa necessária.

## 4. Thumbnail
O usuário cria a capa numa IA externa. Escreva em `videos/<slug>/thumb_prompts.md`
2 prompts em inglês (16:9): um rosto com emoção forte + objeto destacado com
seta/círculo vermelho, texto grande de 3–4 palavras com contorno preto (branco +
amarelo ou vermelho), texto à direita. Mostre os prompts na resposta.
Se ele mandar a imagem, salve como `videos/<slug>/thumb.png` (1280×720) e,
se o vídeo já foi enviado, use o YouTube Studio ou reenvie só a capa.

## 5. Entregar
Diga ao usuário: título, duração, link do YouTube Studio (privado), o que conferiu
e o que não conferiu (ex.: não ouviu o áudio inteiro), e os prompts de thumbnail.
Ele aprova e publica no Studio.

## Problemas conhecidos
- **Kaggle sem token**: peça para gerar em Kaggle → Settings → API Tokens e colocar
  `KAGGLE_API_TOKEN=...` no `.env`.
- **Token do YouTube expirado** (app em modo de teste expira em 7 dias):
  `python youtube/upload.py auth --canal <canal>`, o link abre no perfil do
  Chrome da conta do canal (honda: nuvra84@gmail.com, gesund: felipegodoydark@gmail.com).
- **Voz não encontrada** no Cartesia: liste as vozes do idioma pela API e peça
  para o usuário escolher; atualize `canais.json`.
- **Cota do YouTube**: ~6 envios por dia somando os dois canais.
