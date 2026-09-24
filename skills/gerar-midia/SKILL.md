---
name: gerar-midia
description: Gera a imagem ou carrossel de um post seguindo a paleta e tipografia da marca, e sobe para um local com URL pública (necessário para publicação via API). Use depois de planejar-post.
---

# Gerar Mídia

1. Use `config/brand.yaml` (ou `config/marcas/<marca>.yaml`) para cores/fontes —
   as cores dos slides vêm de `cores_slide`. Script:
   `python scripts/gerar_midia.py [--marca <marca>] --data <data>`.
2. Gere a imagem (matplotlib/PIL, como os diagramas do material principal)
   ou o carrossel (uma imagem por slide).
3. Salve em `queue/media/<data>-slide<n>.png` (ou `queue/<marca>/media/`).
4. Se for usar a Rota B (Graph API), a mídia PRECISA estar acessível por
   URL pública no momento da publicação — suba para o bucket configurado
   em `PUBLIC_MEDIA_BASE_URL` antes de marcar o post como pronto.
   A Rota A (Buffer) também recebe as imagens por URL pública
   (`PUBLIC_MEDIA_BASE_URL`), então o mesmo vale para ela.
5. Atualize `queue/[<marca>/]<data>.json` com o(s) caminho(s) da mídia e status
   "pronto_para_aprovacao".
