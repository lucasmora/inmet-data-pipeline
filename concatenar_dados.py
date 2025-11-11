import os
import re
import pandas as pd

caminho_dos_arquivos = r"C:\\Users\\moral\\Downloads\\meteorologia"

padrao_arquivo = re.compile(r"INMET_(?P<regiao>[A-Z]{1,2})_"
    r"(?P<estado>[A-Z]{2})_"
    r"(?P<estacao>[A-Z]\d{3})_"
    r"(?P<cidade>[A-Za-zÀ-ÿ0-9().\-\s]+)_")

lista_dfs = []

# Abrir pasta
for arq in os.listdir(caminho_dos_arquivos):
    if arq.endswith(".CSV"):
        caminho_arquivo = os.path.join(caminho_dos_arquivos, arq)
        resultado = padrao_arquivo.search(arq)
        if not resultado:
            print(f"Padrão não encontrado em {arq}.")
            continue

        dados = resultado.groupdict()
        
        df = pd.read_csv(os.path.join(caminho_dos_arquivos, arq), skiprows=8, sep=";", encoding='latin_1')
        df.insert(2, "regiao", dados['regiao'])
        df.insert(3, "estado", dados['estado'])
        df.insert(4, "estacao", dados['estacao'])
        df.insert(5, "cidade", dados['cidade'])
        
        lista_dfs.append(df)
    
df_final = pd.concat(lista_dfs, ignore_index=True)
print(df_final.shape)