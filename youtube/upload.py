"""Upload de vídeos para o YouTube, sempre como PRIVADO (você aprova no YouTube Studio).

Cada canal tem seu próprio token, então os dois canais nunca se misturam.

Uso:
  python youtube/upload.py auth   --canal honda
  python youtube/upload.py auth   --canal gesund
  python youtube/upload.py upload --canal honda --video honda-teste/honda_teste.mp4 \
      --titulo "..." --descricao "..." --tags "honda,civic" [--thumb capa.png]

Arquivos (nunca vão para o git):
  youtube/client_secret.json      credencial OAuth do Google Cloud (tipo "App para computador")
  youtube/tokens/<canal>.json     token de cada canal, criado no comando `auth`
"""
import argparse, pathlib, sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE = pathlib.Path(__file__).parent
CLIENT_SECRET = BASE / "client_secret.json"
TOKENS = BASE / "tokens"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

CANAIS = {
    "honda":  {"nome": "Honda Deep Dive", "idioma": "en", "categoria": "2"},   # Autos & Vehicles
    "gesund": {"nome": "Gesund ab 60",    "idioma": "de", "categoria": "27"},  # Education
}


def credenciais(canal: str, autorizar: bool = False) -> Credentials:
    token = TOKENS / f"{canal}.json"
    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        if not autorizar:
            sys.exit(f"Canal '{canal}' ainda não autorizado. Rode: python youtube/upload.py auth --canal {canal}")
        if not CLIENT_SECRET.exists():
            sys.exit(f"Falta {CLIENT_SECRET}. Baixe a credencial OAuth do Google Cloud (veja youtube/README.md).")
        print(f"\nNo navegador, entre com a conta Google e ESCOLHA O CANAL '{CANAIS[canal]['nome']}'.\n")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
        # não abre o navegador sozinho: cada canal pode estar num perfil diferente do Chrome
        creds = flow.run_local_server(port=0, prompt="consent", open_browser=False,
                                      authorization_prompt_message="Abra este link no perfil do Chrome do canal:\n{url}\n")
    TOKENS.mkdir(exist_ok=True)
    token.write_text(creds.to_json(), encoding="utf-8")
    return creds


def upload(a):
    cfg = CANAIS[a.canal]
    yt = build("youtube", "v3", credentials=credenciais(a.canal))
    body = {
        "snippet": {
            "title": a.titulo[:100],
            "description": a.descricao,
            "tags": [t.strip() for t in a.tags.split(",") if t.strip()],
            "categoryId": cfg["categoria"],
            "defaultLanguage": cfg["idioma"],
            "defaultAudioLanguage": cfg["idioma"],
        },
        "status": {
            "privacyStatus": "private",          # sempre privado: você aprova no Studio
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,      # declara conteúdo gerado por IA
        },
    }
    media = MediaFileUpload(a.video, chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"enviando... {int(status.progress() * 100)}%")
    vid = resp["id"]
    if a.thumb:
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(a.thumb)).execute()
    print(f"OK ({cfg['nome']}, privado): https://studio.youtube.com/video/{vid}/edit")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("auth"); pa.add_argument("--canal", choices=CANAIS, required=True)
    pu = sub.add_parser("upload"); pu.add_argument("--canal", choices=CANAIS, required=True)
    pu.add_argument("--video", required=True); pu.add_argument("--titulo", required=True)
    pu.add_argument("--descricao", default=""); pu.add_argument("--tags", default="")
    pu.add_argument("--thumb")
    a = p.parse_args()
    if a.cmd == "auth":
        credenciais(a.canal, autorizar=True)
        print(f"Canal '{CANAIS[a.canal]['nome']}' autorizado.")
    else:
        upload(a)


if __name__ == "__main__":
    main()
