# 🦮 Chatbot — Cão-Guia Digital

> **Inteligência artificial e acessibilidade para facilitar o acesso às informações do Programa Cão-Guia.**

O **Chatbot Cão-Guia Digital** é um módulo do projeto de extensão desenvolvido no **IF Goiano – Campus Urutaí**, com o objetivo de oferecer um assistente virtual capaz de responder dúvidas sobre o Programa Cão-Guia.

O sistema utiliza **inteligência artificial e recuperação de informações em documentos**, permitindo que os usuários consultem conteúdos relacionados ao programa por meio de uma interface simples e acessível.

O chatbot foi desenvolvido em Python e funciona como um serviço independente, preparado para integração com o portal Cão-Guia Digital.

---

## 🎯 Objetivos

O chatbot tem como principais objetivos:

- 🤖 Facilitar o acesso às informações sobre o Programa Cão-Guia;
- 📚 Responder dúvidas com base em documentos de referência;
- ♿ Oferecer uma interface acessível para pessoas com deficiência visual;
- 💬 Permitir uma interação simples entre o usuário e o assistente;
- 🔎 Auxiliar na consulta de informações sobre treinamento, voluntariado e participação no programa;
- 🌐 Complementar as funcionalidades do portal Cão-Guia Digital.

---

## 🛠️ Tecnologias

As principais tecnologias utilizadas no desenvolvimento são:

- **Python** — linguagem utilizada no desenvolvimento do chatbot;
- **FastAPI** — construção da API responsável pela comunicação com o sistema;
- **Ollama** — execução local do modelo de linguagem;
- **Qwen 2.5** — modelo de linguagem utilizado para gerar as respostas;
- **RAG (Retrieval-Augmented Generation)** — recuperação de informações para contextualizar as respostas;
- **Sentence Transformers** — geração de embeddings para busca semântica;
- **FAISS** — indexação e busca vetorial;
- **HTML5, CSS3 e JavaScript** — desenvolvimento da interface web.

---

## 🧠 Funcionamento

O chatbot utiliza a arquitetura **RAG (Retrieval-Augmented Generation)** para consultar informações armazenadas em sua base de conhecimento antes de gerar uma resposta.

O funcionamento ocorre da seguinte maneira:

1. O usuário envia uma pergunta pela interface.
2. A pergunta é convertida em uma representação vetorial.
3. O FAISS identifica os trechos mais relacionados nos documentos disponíveis.
4. Os trechos recuperados são encaminhados ao modelo de linguagem.
5. O LLM gera uma resposta com base nas informações encontradas.
6. A resposta é apresentada ao usuário.

Quando não encontra informações suficientes, o assistente é orientado a informar essa limitação.

A base inicial contém a especificação de requisitos do Cão-Guia Digital e conteúdos de referência publicados pelo IF Goiano.

---

## ♿ Acessibilidade

A interface do chatbot foi desenvolvida considerando a acessibilidade como um dos requisitos principais do projeto.

Entre os recursos implementados estão:

- ⌨️ Navegação por teclado;
- 👁️ Modo de alto contraste;
- 🔊 Leitura das respostas em voz alta;
- 💻 Compatibilidade estrutural com leitores de tela;
- 📱 Layout responsivo para computadores, tablets e celulares;
- 📝 Organização clara das mensagens e dos elementos da interface.

O módulo ainda necessita de validações adicionais de acessibilidade antes de sua disponibilização definitiva.

---

## 📂 Estrutura do Projeto

```text
chatbot/
├── app/
│   ├── main.py
│   ├── rag.py
│   ├── knowledge_base.py
│   ├── transcription.py
│   └── schemas.py
├── web/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── data/
│   └── documents/
├── tests/
├── config.py
├── ingest.py
├── requirements.txt
└── README.md
```

**Organização principal:**

- `app/` — API e processamento das perguntas;
- `web/` — interface e recursos de acessibilidade;
- `data/documents/` — documentos utilizados na base de conhecimento;
- `tests/` — testes do módulo;
- `config.py` — configurações do sistema;
- `ingest.py` — processamento e indexação dos documentos;
- `requirements.txt` — dependências necessárias para execução.

---

## ⚙️ Como Executar

### Pré-requisitos

- Python instalado;
- Ollama instalado e em execução;
- Dependências disponíveis no arquivo `requirements.txt`.

### Execução em desenvolvimento

Na pasta do chatbot, execute:

```bash
python -m pip install -r requirements.txt
```

Baixe o modelo de linguagem:

```bash
ollama pull qwen2.5:1.5b
```

Prepare a base de conhecimento:

```bash
python ingest.py
```

Inicie a API:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

A interface estará disponível em:

`http://127.0.0.1:8001/`

A documentação da API pode ser acessada em:

`http://127.0.0.1:8001/docs`

O módulo também pode ser executado no **Google Colab** durante o desenvolvimento e os testes.

---

## 🔗 Integração com o Portal

O chatbot foi estruturado para funcionar de maneira independente do backend principal do Cão-Guia Digital.

A comunicação ocorre por meio de uma API REST desenvolvida com FastAPI, que permite receber perguntas e retornar respostas para outras aplicações.

O módulo poderá ser integrado ao frontend do portal e ao backend desenvolvido em Java com Spring Boot.

A integração com o sistema principal está em desenvolvimento.

---

## 👥 Desenvolvimento

Projeto desenvolvido no **IF Goiano – Campus Urutaí**, no curso de **Bacharelado em Sistemas de Informação**.

**Responsável pelo módulo de chatbot:**

- Khauan Heidymon dos Santos Miranda

---

## 📌 Status

🚧 **Em desenvolvimento**

O chatbot possui uma versão funcional para testes e está sendo aprimorado para sua integração com o portal Cão-Guia Digital.

---

## 🏫 Instituição

**Instituto Federal Goiano — Campus Urutaí**

**Curso:** Bacharelado em Sistemas de Informação

---

### 🦮 Cão-Guia Digital

**Tecnologia, informação e acessibilidade a serviço da inclusão.**
