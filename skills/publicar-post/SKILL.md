---
name: publicar-post
description: Publica (ou agenda) um post já aprovado na fila. Use scripts/publicar_buffer.py (Rota A) ou scripts/publicar_graph_api.py (Rota B) — nunca publique um post cujo status em queue/ não seja "aprovado".
---

# Publicar Post

1. NUNCA publique um item de `queue/` com status diferente de "aprovado".
   Isso é a barreira de revisão humana — não pule esta checagem.
2. Rota A (Buffer): scripts/publicar_buffer.py <data>
3. Rota B (Graph API): scripts/publicar_graph_api.py <data>
   (container de mídia → publicar container, respeitando o limite de
   25 posts/24h da API do Instagram)
4. Após publicar com sucesso, mova o item de queue/ para queue/publicados/
   e registre o ID retornado pela API.
