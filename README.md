# Consolidação e limpeza de dados meteorológicos do INMET com Python

Este projeto tem como objetivo automatizar a **leitura, integração e preparação de dados meteorológicos** fornecidos pelo **INMET (Instituto Nacional de Meteorologia)**.  
Ele reúne centenas de arquivos CSV em um único dataset padronizado, facilitando análises em ferramentas como **Power BI**, **Excel** ou **Python**.

---

## Objetivo

Consolidar e preparar dados climáticos de diferentes estações do Brasil, permitindo análises sobre **temperatura, umidade, precipitação, pressão e radiação solar** de forma centralizada e limpa.

---

## Estrutura do Projeto

```
📁 meteorologia/
├── concatena_dados.py        # Extrai e une os arquivos CSV brutos
├── limpeza_dados.py          # Limpa e padroniza os dados
├── dados_estacoes.csv        # Saída gerada após a concatenação
└── dados_estacoes_limpo.csv  # Saída final após limpeza
```

---

## Etapas do Processo

### 1. Coleta e Concatenação (`concatena_dados.py`)
- Lê automaticamente todos os arquivos `.CSV` em um diretório.  
- Usa **expressões regulares (regex)** para extrair metadados (região, estado, estação e cidade) do nome de cada arquivo.  
- Remove colunas vazias e insere colunas descritivas.  
- Concatena os DataFrames em um único arquivo (`dados_estacoes.csv`).

---

### 2. Limpeza e Padronização (`limpeza_dados.py`)

Esta etapa faz a **limpeza e transformação** do dataset gerado, preparando-o para análise em ferramentas de Business Intelligence.

Objetivos:
- Padronizar nomes de colunas (sem espaços, acentos e caracteres especiais);  
- Converter formatos numéricos (ex.: “12,3” → 12.3);  
- Corrigir tipos de dados;  
- Gerar uma saída final: `dados_estacoes_limpo.csv`.

---

## Sobre o Dataset do INMET

Os dados foram obtidos do **Instituto Nacional de Meteorologia (INMET)** e representam medições realizadas em diversas estações meteorológicas do Brasil.

Cada arquivo contém registros horários com variáveis como:

| Variável | Descrição |
|-----------|------------|
| `Data` | Data da observação |
| `Hora (UTC)` | Horário da coleta |
| `PRECIPITAÇÃO TOTAL, HORÁRIO (mm)` | Quantidade de chuva registrada |
| `PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (mB)` | Pressão atmosférica ao nível da estação |
| `RADIACAO GLOBAL (Kj/m²)` | Energia solar recebida |
| `TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)` | Temperatura instantânea do ar |
| `TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C)` | Temperatura máxima registrada na hora anterior |
| `TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C)` | Temperatura mínima registrada na hora anterior |
| `UMIDADE RELATIVA DO AR, HORARIA (%)` | Umidade relativa do ar |
| `VENTO, VELOCIDADE HORARIA (m/s)` | Velocidade do vento |

Essas variáveis permitem análises sobre:
- Variação de temperatura e umidade ao longo do tempo;  
- Comparações regionais entre estados e estações;  
- Identificação de padrões de chuva e períodos de seca;  
- Estudos de comportamento climático local.

---

## Tecnologias e Bibliotecas utilizadas

- **Python 3**
- **Pandas** → manipulação e concatenação de dados 
- **Regex (re)** → extração de informações dos nomes dos arquivos  
- **OS** → automação da leitura de diretórios

---

## Habilidades Demonstradas

- Manipulação e limpeza de dados com **Pandas**  
- Uso de **expressões regulares** para automação  
- Construção de pipeline de dados (extração → transformação → exportação)  
- Preparação de datasets para **análise em Power BI**

---

## Próximos Passos

- Implementar as etapas de limpeza e transformação em `limpeza_dados.py`  
- Criar gráficos e relatórios analíticos no Power BI  
- Explorar padrões climáticos regionais com análises estatísticas

---

## Fluxo ETL Simplificado

```
[Arquivos CSV brutos]
        ↓
 concatena_dados.py  →  dados_estacoes.csv
        ↓
 limpeza_dados.py    →  dados_estacoes_limpo.csv
        ↓
   Power BI / Análises
```

---

## Contato

**Lucas Môra**  
[LinkedIn](https://www.linkedin.com/in/lucas-mora-) • [GitHub](https://github.com/lucasmora)
