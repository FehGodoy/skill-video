"""Monta o vídeo no estilo "colagem explicativa".

Fundo branco, título da cena no topo, imagens e rótulos que vão aparecendo
sincronizados com a narração, tópicos em lista e legenda com palavra-chave em vermelho.

Uso: python motor/montar.py videos/<slug>
Precisa de: roteiro.json, narracao.json, audio/cena_XX.wav, imagens/<id>.png
Saída: videos/<slug>/video.mp4
"""
import json, pathlib, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps

RAIZ = pathlib.Path(__file__).resolve().parent.parent
W, H = 1920, 1080
FONTE = "C:/Windows/Fonts/comicbd.ttf"
PAUSA = 0.6                     # silêncio no fim de cada cena
AREA = (60, 150, 1860, 900)     # região das imagens (x0, y0, x1, y1); legenda fica abaixo
COLUNA_TOPICOS = 560            # largura reservada à direita quando a cena tem tópicos
FUNDO = (252, 251, 248)


def fonte(t):
    return ImageFont.truetype(FONTE, t)


def grade(n, x0, y0, x1, y1):
    """Retângulos (x, y, w, h) para n imagens, deixando espaço para o rótulo embaixo."""
    if n <= 0:
        return []
    cols = {1: 1, 2: 2, 3: 3, 4: 2, 5: 3, 6: 3}.get(n, 3)
    rows = -(-n // cols)
    gap, rot = 40, 70
    cw = (x1 - x0 - gap * (cols - 1)) / cols
    ch = (y1 - y0 - gap * (rows - 1)) / rows - rot
    w = min(cw, ch * 16 / 9); h = w * 9 / 16
    out = []
    for i in range(n):
        r, c = divmod(i, cols)
        na_linha = min(cols, n - r * cols)
        larg_linha = na_linha * w + (na_linha - 1) * gap
        xs = x0 + (x1 - x0 - larg_linha) / 2
        alt_total = rows * (h + rot) + (rows - 1) * gap
        ys = y0 + (y1 - y0 - alt_total) / 2
        out.append((int(xs + c * (w + gap)), int(ys + r * (h + rot + gap)), int(w), int(h)))
    return out


def quadro(titulo, imgs, topicos, pasta):
    """imgs: lista de (id, rotulo, slot); topicos: lista de str visíveis."""
    im = Image.new("RGB", (W, H), FUNDO)
    d = ImageDraw.Draw(im)
    ft = fonte(66)
    tw = d.textlength(titulo, font=ft)
    d.text(((W - tw) / 2, 38), titulo, font=ft, fill=(20, 20, 20))
    d.line([((W - tw) / 2, 122), ((W + tw) / 2, 122)], fill=(220, 40, 40), width=6)
    fr = fonte(38)
    for iid, rot, (x, y, w, h) in imgs:
        p = pasta / "imagens" / f"{iid}.png"
        if not p.exists():
            continue
        foto = ImageOps.fit(Image.open(p).convert("RGB"), (w, h))
        sombra = Image.new("RGB", (w + 16, h + 16), (215, 213, 208))
        im.paste(sombra, (x - 4, y - 4))
        im.paste(foto, (x, y))
        lw = d.textlength(rot, font=fr)
        d.text((x + (w - lw) / 2, y + h + 12), rot, font=fr, fill=(25, 25, 25))
    if topicos:
        larg = COLUNA_TOPICOS - 40 if imgs else 1400
        tam = 60
        while tam > 30 and max(d.textlength("- " + t, font=fonte(tam)) for t in topicos) > larg:
            tam -= 2
        fb = fonte(tam)
        x0 = AREA[2] - COLUNA_TOPICOS + 20 if imgs else (W - max(d.textlength("- " + t, font=fb) for t in topicos)) / 2
        passo = int(tam * 1.9)
        y = AREA[1] + (AREA[3] - AREA[1] - len(topicos) * passo) / 2
        for t in topicos:
            d.text((x0, y), "- " + t, font=fb, fill=(20, 20, 20))
            y += passo
    return im


def cena_eventos(cena, info):
    """Lista de (tempo, imagens_visiveis, topicos_visiveis) para a cena.

    As imagens entram em "páginas" de até 3 (2 se a cena tem tópicos): quando a
    página enche, a tela limpa e a próxima começa, para as fotos ficarem grandes.
    """
    todas = [im for f in cena["falas"] for im in f.get("imagens", [])]
    tem_top = any(f.get("topicos") for f in cena["falas"])
    x0, y0, x1, y1 = AREA
    if tem_top and todas:
        x1 -= COLUNA_TOPICOS
    por_pag = 2 if tem_top else 3
    # páginas montadas por fala (as imagens de uma mesma fala nunca se separam)
    paginas, atual = [], []
    for f in cena["falas"]:
        ims = f.get("imagens", [])
        if ims and atual and len(atual) + len(ims) > por_pag:
            paginas.append(atual); atual = []
        atual += ims
    if atual:
        paginas.append(atual)
    slot_de, inicio_pag = {}, set()
    for pg in paginas:
        inicio_pag.add(pg[0]["id"])
        for im, s in zip(pg, grade(len(pg), x0, y0, x1, y1)):
            slot_de[im["id"]] = s
    eventos, vis_i, vis_t = [(0.0, [], [])], [], []
    for fi, f in enumerate(cena["falas"]):
        t = info["falas_inicio"][fi]
        for im in f.get("imagens", []):
            if im["id"] in inicio_pag:
                vis_i = []          # nova página
            vis_i.append((im["id"], im["rotulo"], slot_de[im["id"]]))
        if f.get("imagens"):
            eventos.append((t, list(vis_i), list(vis_t)))
        if f.get("topicos"):
            # tópicos de uma fala nova substituem os anteriores
            if f.get("imagens"):
                t += 0.4
            for j, tp in enumerate(f["topicos"]):
                tt = t + j * 0.6
                vis_t = (vis_t if j else []) + [tp]
                eventos.append((tt, list(vis_i), list(vis_t)))
    return eventos


def ass_tempo(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def legendas(rot, narr, deslocs):
    chaves = set()
    for c in rot["cenas"]:
        for f in c["falas"]:
            for m in re.findall(r"\*([^*]+)\*", f["texto"]):
                chaves.update(re.sub(r"[^\w-]", "", w).lower() for w in m.split())
    ass = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "",
           "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginV",
           "Style: L,Comic Sans MS,58,&H00141414,&H00F8FBFC,&H00000000,-1,1,3,0,2,48", "",
           "[Events]", "Format: Layer, Start, End, Style, Text"]
    for info, base in zip(narr, deslocs):
        pal, ini, fim = info["palavras"], info["inicio"], info["fim"]
        i = 0
        while i < len(pal):
            j = i
            while j < len(pal) and j - i < 6:
                j += 1
                if re.search(r"[.,!?;:]$", pal[j - 1]):
                    break
            txt = []
            for w in pal[i:j]:
                lw = re.sub(r"[^\w-]", "", w).lower()
                txt.append("{\\c&H2828DC&}" + w + "{\\c&H141414&}" if lw in chaves else w)
            fim_bloco = ini[j] if j < len(ini) else fim[j - 1] + 0.3
            ass.append(f"Dialogue: 0,{ass_tempo(base + ini[i])},{ass_tempo(base + fim_bloco)},L,{' '.join(txt)}")
            i = j
    return "\n".join(ass)


def main():
    pasta = RAIZ / sys.argv[1]
    rot = json.loads((pasta / "roteiro.json").read_text(encoding="utf-8"))
    narr = json.loads((pasta / "narracao.json").read_text(encoding="utf-8"))
    tmp = pasta / "tmp"; (tmp / "q").mkdir(parents=True, exist_ok=True)
    lista, audios, deslocs, t_global = [], [], [], 0.0
    for ci, (cena, info) in enumerate(zip(rot["cenas"], narr), 1):
        dur = info["duracao"] + PAUSA
        evs = cena_eventos(cena, info)
        for ei, (t, imgs, tops) in enumerate(evs):
            fim = evs[ei + 1][0] if ei + 1 < len(evs) else dur
            if fim - t < 0.04:
                continue
            arq = tmp / "q" / f"c{ci:02d}_{ei:02d}.png"
            quadro(cena["titulo"], imgs, tops, pasta).save(arq)
            lista.append((arq, fim - t))
        audios.append(pasta / "audio" / f"cena_{ci:02d}.wav")
        deslocs.append(t_global)
        t_global += dur
        print(f"cena {ci:02d}: {len(evs)} quadros")
    # vídeo de quadros (concat com durações)
    txt = "".join(f"file '{a.as_posix()}'\nduration {d:.3f}\n" for a, d in lista) + f"file '{lista[-1][0].as_posix()}'\n"
    (tmp / "quadros.txt").write_text(txt, encoding="utf-8")
    # áudio: cenas + pausa
    filt = "".join(f"[{i}:a]apad=pad_dur={PAUSA}[a{i}];" for i in range(len(audios)))
    filt += "".join(f"[a{i}]" for i in range(len(audios))) + f"concat=n={len(audios)}:v=0:a=1[out]"
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for a in audios:
        cmd += ["-i", str(a)]
    subprocess.run(cmd + ["-filter_complex", filt, "-map", "[out]", "-ar", "44100", str(tmp / "narracao.wav")], check=True)
    (tmp / "legendas.ass").write_text(legendas(rot, narr, deslocs), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "quadros.txt",
                    "-i", "narracao.wav", "-vf", "fps=30,format=yuv420p,subtitles=legendas.ass",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "../video.mp4"], cwd=tmp, check=True)
    print(f"pronto: {pasta / 'video.mp4'} ({t_global / 60:.1f} min)")


if __name__ == "__main__":
    main()
