"""Thumbnail 1280x720 no estilo dos canais: foto forte + texto grande com contorno.

Uso: python motor/thumb.py videos/<slug> <id_imagem> "LINHA 1" "LINHA 2" ["LINHA 3"]
A última linha sai em destaque (amarelo, ou vermelho se começar com '!').
"""
import pathlib, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance

RAIZ = pathlib.Path(__file__).resolve().parent.parent
W, H = 1280, 720
IMPACT = "C:/Windows/Fonts/impact.ttf"

pasta = RAIZ / sys.argv[1]
foto = Image.open(pasta / "imagens" / f"{sys.argv[2]}.png").convert("RGB")
img = ImageOps.fit(foto, (W, H))
img = ImageEnhance.Contrast(ImageEnhance.Color(img).enhance(1.25)).enhance(1.15)
# escurece a metade direita para o texto
grad = Image.linear_gradient("L").rotate(90).resize((W, H))
img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, grad.point(lambda v: int(v * 0.75)))
d = ImageDraw.Draw(img)
linhas = sys.argv[3:]
y = 60
for i, txt in enumerate(linhas):
    destaque = i == len(linhas) - 1
    cor = (255, 214, 0) if destaque else (255, 255, 255)
    if txt.startswith("!"):
        txt, cor = txt[1:], (235, 30, 40)
    tam = 150
    while True:
        f = ImageFont.truetype(IMPACT, tam)
        if d.textlength(txt, font=f) <= W * 0.56 or tam < 60:
            break
        tam -= 6
    x = W - 40 - d.textlength(txt, font=f)
    d.text((x, y), txt, font=f, fill=cor, stroke_width=10, stroke_fill=(0, 0, 0))
    y += int(tam * 1.08)
img.save(pasta / "thumb.png")
print(pasta / "thumb.png")
