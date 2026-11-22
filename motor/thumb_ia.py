"""Gera a thumbnail com a API de imagens da OpenAI (modelo do ChatGPT) e salva thumb.png 1280x720.

Uso: python motor/thumb_ia.py videos/<slug> [--refazer]
Prompt: campo "thumb_prompt" do roteiro.json.
Requer OPENAI_API_KEY no .env. Custo: cobrado na sua conta da OpenAI (poucos centavos por imagem).
"""
import base64, io, json, os, pathlib, sys

import requests
from PIL import Image, ImageOps

RAIZ = pathlib.Path(__file__).resolve().parent.parent
for linha in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in linha and not linha.strip().startswith("#"):
        k, v = linha.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

MODELO = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2")


def main():
    pasta = RAIZ / sys.argv[1]
    destino = pasta / "thumb.png"
    if destino.exists() and "--refazer" not in sys.argv:
        print(f"já existe: {destino} (use --refazer para gerar outra)"); return
    chave = os.environ.get("OPENAI_API_KEY")
    if not chave:
        raise SystemExit("Falta OPENAI_API_KEY no .env.")
    rot = json.loads((pasta / "roteiro.json").read_text(encoding="utf-8"))
    prompt = rot.get("thumb_prompt")
    if not prompt:
        raise SystemExit("O roteiro não tem 'thumb_prompt'.")
    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"},
        # 1536x864 já é 16:9: nada é cortado na hora de virar 1280x720
        # padrão "medium": mais barato e rápido, e suficiente para 1280x720.
        # Só use --alta se a média sair com texto ou detalhes ruins.
        json={"model": MODELO, "prompt": prompt, "size": "1536x864",
              "quality": "high" if "--alta" in sys.argv else "medium", "n": 1},
        timeout=300,
    )
    if r.status_code != 200:
        raise SystemExit(f"OpenAI respondeu {r.status_code}: {r.text[:400]}")
    dados = r.json()
    if dados.get("usage"):
        (pasta / "thumb_uso.json").write_text(json.dumps(dados["usage"]), encoding="utf-8")
        print(f"uso: {dados['usage']}")
    img = Image.open(io.BytesIO(base64.b64decode(dados["data"][0]["b64_json"]))).convert("RGB")
    ImageOps.fit(img, (1280, 720), Image.LANCZOS).save(destino, optimize=True)
    print(f"thumbnail salva: {destino}")


if __name__ == "__main__":
    main()
