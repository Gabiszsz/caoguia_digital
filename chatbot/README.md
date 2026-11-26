# Cão-Guia Digital — chatbot acessível para Google Colab

**Projeto acadêmico independente** que utiliza **Python, FastAPI, Ollama (LLM Qwen 2.5), RAG, Sentence Transformers e FAISS**. Não altera o backend Java/Spring Boot, banco de dados ou outras funcionalidades do portal.

## Execute no Google Colab

**Arquivo recomendado:** `Chatbot_Cao_Guia_Colab_Atualizado_IFGoiano.ipynb`, distribuído junto deste projeto. O notebook é **autocontido**: o código do chatbot e a especificação de requisitos em PDF estão incorporados nele. Você só precisa importar o `.ipynb` no Google Colab, sem enviar outro ZIP.

1. Abra https://colab.research.google.com/ e faça upload do `.ipynb`.
2. Se possível, configure **Ambiente de execução > Alterar tipo de ambiente de execução > T4 GPU**.
3. Execute as células **em ordem**. A instalação inclui `zstd` ANTES do Ollama (corrigindo o erro de extração anterior).
4. A célula de indexação gera a base FAISS a partir da SRS v1.3 e de resumos das páginas oficiais do IF Goiano, com URLs preservadas.
5. A etapa 8 oferece um link para **abrir o chatbot em uma aba HTTPS separada** e também uma visualização embutida opcional. Em iframe o navegador pode bloquear o microfone.
6. Mantenha a sessão do Colab aberta enquanto usar o sistema. Não há URL pública nem túnel anônimo.

Se a execução for interrompida/reiniciada, rode novamente as células. Em sessões gratuitas, duração e memória variam; o download do LLM requer conexão e espaço. O modelo padrão é `qwen2.5:3b`; caso a sessão não tenha memória suficiente, configure `qwen2.5:1.5b` na célula de modelo.

## Acessibilidade incluída

- Estrutura semântica (`header`, `main`, `aside`, títulos, campos rotulados), link para pular direto à pergunta, rótulos de controles e botões.
- Histórico de mensagens disponível para leitores de tela; atualização anunciada em região `aria-live` e indicador de carregamento `role=status`.
- Navegação completa com **Tab**, **Shift+Tab**, **Enter**, **Shift+Enter**, foco visível, atalhos opcionais **Alt+Q** e **Esc** para interromper leitura.
- Controle de tamanho de texto (100% a 145%) e modo de alto contraste; layouts responsivos para desktop, tablet e celular.
- Botões para **ouvir** e **parar** a leitura por voz das respostas; leitura automática opcional pelo sistema de síntese de voz do navegador.
- **Novo microfone:** gravação via `MediaRecorder` e transcrição em português com Whisper (faster-whisper) no backend Python. Clique uma vez para iniciar e outra para terminar; confira o texto antes de enviar. A primeira transcrição baixa o modelo Whisper e pode demorar.
- **Apenas um botão de microfone:** não há opção de enviar arquivo de áudio. Em caso de bloqueio no iframe, use a abertura em uma aba HTTPS independente e autorize o microfone no navegador.
- O navegador precisa autorizar o microfone. Algumas políticas de iframe do Colab impedem a captura mesmo com código correto; nesse caso, abra em aba separada na etapa 8. Se continuar bloqueado, verifique a configuração do Chrome, o Windows e se a página HTTPS permite o dispositivo.
- Respeito à preferência do sistema por movimento reduzido; botões e áreas de toque dimensionados para interação mais fácil.

**Importante:** leitura por voz do navegador não substitui leitor de tela. O uso por pessoas com cegueira total depende do leitor de tela (ex.: NVDA/VoiceOver), do navegador e da configuração de foco. **A conformidade WCAG 2.2 não foi certificada**: é necessária avaliação com usuários, testes manuais com teclado, leitores de tela e auditoria antes da publicação.

## Dados e responsabilidade

Os documentos consultados são mantidos na API, sem etiquetas sob a resposta na interface. As fontes iniciais são o documento acadêmico `Especificacao_Requisitos_Cao_Guia_Digital_v1.3.pdf`, que **descreve funcionalidades planejadas do portal**, e resumos referenciados de quatro páginas oficiais do IF Goiano, verificados em 24/11/2026. Os documentos consultados são mantidos na API, sem etiquetas sob a resposta na interface. As fontes oficiais possuem suas datas e podem ficar desatualizadas. O chatbot não consulta automaticamente novas publicações e nunca deve afirmar a disponibilidade atual de vagas sem confirmação.

O RAG busca trechos desse documento e pede ao LLM que responda apenas com base neles. Ele pode errar ou omitir informações: a interface mostra a origem e a página para revisão, e o modelo é orientado a dizer quando não sabe. Um trecho recuperado **não garante** que uma resposta foi factualmente sustentada.

Adicione PDFs, DOCX, TXT ou MD oficiais à pasta `data/documents` e rode `python ingest.py` novamente. Não indexe documentos pessoais, laudos, telefones privados ou cadastros de participantes. PDF digitalizado em imagem pode não ser extraído sem OCR.

## Pastas

```text
CaoGuia_Colab_Acessivel/
├── app/                 # API, schemas, busca FAISS e conexão Ollama
├── data/documents/      # Documento fornecido e documentos adicionais
├── data/index/          # Indexação gerada na execução
├── web/                 # Página responsiva e acessível HTML/CSS/JavaScript
├── tests/               # Testes de API e interface
├── config.py
├── ingest.py
├── requirements.txt
└── README.md
```

## API

- `GET /` — interface web.
- `GET /api/v1/health` — confirma a presença do índice FAISS.
- `GET /api/v1/model/status` — testa conexão local ao Ollama e instalação do LLM.
- `POST /api/v1/chat` — JSON `{"message": "Qual é o objetivo do portal?"}`.
- `POST /api/v1/transcribe` — recebe `multipart/form-data` com um campo `audio`, transcreve em português com Whisper local (até 15 MB, primeiros 75 segundos) e devolve `{"text": "...", "language": "pt-BR"}`.

Exemplo de resposta:

```json
{
  "answer": "...",
  "sources_found": true,
  "sources": [{"document": "Especificacao_Requisitos_Cao_Guia_Digital_v1.3.pdf", "page": 4, "score": 0.61}],
  "response_time_ms": 4234
}
```

`score`, `sources_found` e o texto de resposta acima são **exemplificativos** e não equivalem a validação factual. O projeto não registra mensagens em banco nem consulta o backend Java.

## Segurança e implantação

O notebook usa visualização do próprio Colab em porta local, sem abrir Cloudflare Tunnel; nenhuma autenticação adicional é fornecida para uma exposição pública da API. Não exponha o servidor diretamente na Internet. Antes de uso público, adicionar HTTPS, autenticação e limites de uso onde necessário, políticas de privacidade, revisão de documentos, CORS estrito e auditoria de acessibilidade.

## Rodar localmente, opcional

```bash
python -m pip install -r requirements.txt
# Instale/inicie o Ollama separadamente e baixe qwen2.5:3b.
python ingest.py
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Abra `http://127.0.0.1:8001/`.

## Como testar o microfone no Colab

1. Use o notebook atualizado com **etapas 1 a 8**. A etapa 2 instala também `faster-whisper` e `python-multipart`.
2. Na etapa 8, abra a interface do chatbot e permita o microfone quando o navegador solicitar.
3. Clique no ícone do microfone para iniciar a gravação. Fale por alguns segundos e clique novamente para terminar.
4. Aguarde a transcrição e confira o texto; clique em Enviar para conversar com o LLM.
5. Se o microfone for bloqueado pelo Colab, tente a opção **Abrir chatbot em outra aba** na etapa 8 e permita o microfone para a página HTTPS. O iframe pode continuar bloqueado.

O áudio NÃO é utilizado pelo LLM diretamente. O Whisper converte fala para texto, depois o fluxo RAG/FAISS/Ollama recebe a pergunta em texto.

## Fontes oficiais incluídas

- https://ifgoiano.edu.br/home/index.php/programa-cao-guia.html — apresentação e formação dos cães.
- https://www.ifgoiano.edu.br/home/index.php/ultimas-noticias/30669-if-goiano-realiza-inscricoes-para-pessoas-com-deficiencia-visual-interessadas-em-receber-cao-guia.html — inscrições e formação de duplas (jun/2026).
- https://www.ifgoiano.edu.br/home/index.php/ultimas-noticias/17-ultimas-noticias/30555-if-goiano-segue-com-inscricoes-abertas-para-candidatos-a-caes-guia.html — informações do edital e contato (mai/2026).
- https://www.ifgoiano.edu.br/home/index.php/ultimas-noticias-urutai/30175-campus-urutai-abre-selecao-de-fluxo-continuo-para-entrega-de-caes-guia-edital-29-2025.html — seleção (mar/2026).
- https://www.ifgoiano.edu.br/home/index.php/component/content/article/458-extensao-urutai/projeto-cao-guia/8892-familia-socializadora.html — voluntariado socializador.

Os textos locais são resumos informativos e identificam as fontes. Consulte os originais para regras e editais completos.


## Correção do microfone (novembro de 2026)

O `faster-whisper` 1.2.1 não é compatível com PyAV 19, que removeu o parâmetro
`metadata_errors` usado no decodificador. Por isso, `requirements.txt` fixa
`av==18.1.0` por compatibilidade, embora o áudio agora seja pré-decodificado por FFmpeg para PCM antes do Whisper. Se você já estiver usando o Colab antigo, execute
`%pip install --force-reinstall --no-deps av==18.1.0`, reinicie a API e tente novamente.
A gravação usa apenas o microfone; não há botão de envio de arquivo de áudio.
Consulte `/content/caoguia_api.log` caso a transcrição ainda falhe.

## Respostas progressivas e otimização para o Colab

O endpoint `POST /api/v1/chat/stream` retorna eventos NDJSON (`start`, `delta`, `done`, `error`). A interface mostra os fragmentos à medida que o Ollama os gera; isso diminui a espera percebida, **não torna a geração instantânea**. A API JSON `/api/v1/chat` permanece disponível. As fontes continuam na API, mas não aparecem nas bolhas de conversa.

Para reduzir o tempo de geração, o RAG seleciona até três trechos e limita a quantidade de texto enviado ao Qwen. Perguntas com múltiplas partes permitem uma resposta um pouco mais longa. O limite de espera passou a 300 segundos para acomodar sessões Colab mais lentas. Em sessões sem GPU, o processamento ainda poderá ser lento.

**Microfone:** a captura utiliza `MediaRecorder`; o FFmpeg converte o áudio em PCM mono de 16 kHz e o Whisper o transcreve. Para isso, a etapa 3 do notebook instala `ffmpeg`. O reconhecimento pode levar tempo, especialmente no primeiro uso, quando o modelo Whisper é baixado.

**Conferência de desempenho:** execute `ollama ps` no Colab após enviar uma pergunta. Se mostrar `100% CPU`, a inferência ocorrerá muito mais lentamente. Escolha GPU T4 nas configurações do Colab, se disponível, e reinicie as etapas. A aceleração depende de o Ollama reconhecer a GPU na sessão.


## Versão acessível e otimizada (Colab)

- O padrão é `qwen2.5:1.5b`, que geralmente gera respostas mais rapidamente do que o 3B,
  com possível perda de detalhamento. Para priorizar qualidade, configure `OLLAMA_MODEL=qwen2.5:3b`
  e baixe o modelo correspondente no Ollama.
- A API carrega previamente o modelo de embeddings quando `PRELOAD_KB=1`.
  As respostas são transmitidas progressivamente; o tempo real depende da GPU/CPU do Colab.
- O Whisper tenta usar o modelo `small` na GPU e recorre ao `base` na CPU. O ditado
  utiliza vocabulário do IF Goiano e busca menos erros sem exigir fala artificialmente lenta.
- A interface utiliza alto contraste, navegação por teclado, leitores de tela e
  leitura opcional das respostas, sem narração por passagem de mouse nem botões de zoom próprios.
- As mensagens de fontes continuam ocultas na interface, mas os metadados são
  preservados na API. O modelo pode errar: confira informações institucionais atualizadas.
- O Colab é temporário, não substitui uma hospedagem de produção. As otimizações
  não garantem tempo máximo de resposta nem transcrição perfeita.


## Versão com microfone estável (26/11/2026)

- O Whisper usa `base` na **CPU por padrão** (`WHISPER_DEVICE=cpu`). A GPU
  continua disponível para o Qwen via Ollama. A utilização da GPU pelo Whisper
  pode ser reativada conscientemente, mas certas instalações do Colab falham
  apenas na inferência CUDA, mesmo após carregar o modelo.
- Ao ocorrer falha de execução durante a transcrição, a API tenta novamente
  com o Whisper na CPU. A iteração dos segmentos é protegida por tratamento de erro.
- `vad_filter=False` no ditado evita falhas adicionais causadas pelo
  detector de voz opcional (ONNX Runtime) em alguns ambientes.
- A etapa 7 do notebook pré-carrega o Whisper e executa uma verificação automática de áudio. Ela
  envia um sinal de teste WebM/Opus à mesma rota usada pelo microfone para
  diagnosticar problemas com FFmpeg e Whisper. O sinal não contém fala; uma
  resposta HTTP 422 por ausência de palavras é um resultado válido do teste.
- O navegador continua precisando de permissão para o microfone, preferindo
  abrir o chatbot em outra aba HTTPS pela etapa 8.
- Em caso de falha persistente, consulte `/content/caoguia_api.log`, pois a
  versão de CPU ou as bibliotecas do Colab ainda podem exigir outro ajuste.


## Interface e desempenho (versão 2.6)

- Durante a geração, a interface mostra somente três pontos animados na mensagem.
- As respostas são exibidas como texto simples, sem marcadores de negrito Markdown (`**`).
- O contexto e o tamanho máximo das respostas foram ajustados para reduzir o trabalho do LLM; perguntas complexas ainda podem demorar quando o Colab usa apenas CPU.
- O streaming usa fragmentos menores para antecipar o primeiro texto.
- Para verificar o hardware do Ollama no Colab, execute `!ollama ps`.
