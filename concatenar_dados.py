import os

caminho_dos_arquivos = "C:\\Users\\moral\\Downloads\\meteorologia"

# Abrir pasta
for arq in os.listdir(caminho_dos_arquivos):
    if arq.endswith(".CSV"):
        import re

        texto = "INMET_CO_DF_A042_BRAZLANDIA_01-01-2024_A_31-12-2024.CSV"
        padrao = r"INMET_(?P<regiao>[A-Z]{2})_(?P<estado>[A-Z]{2})_(?P<estacao>A\d{3})_(?P<cidade>[A-Z]+)_"
        resultado = re.search(padrao, texto)

        if resultado:
            dados = resultado.groupdict()
            print("Região:", dados["regiao"])
            print("Estado:", dados["estado"])
            print("Estação:", dados["estacao"])
            print("Cidade:", dados["cidade"])
        else:
            print("Nenhum padrão encontrado.")
        
        print("")