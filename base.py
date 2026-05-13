import pandas as pd
import os

class BaseArquivo():
    def __init__(self, pasta: str = 'volume'):
        self.pasta = os.path.join(".", pasta)

    def __listar_arquivos_validos(self):
        return [arquivo for arquivo in os.listdir(self.pasta) if arquivo.endswith('.csv')]

    
    def carregar_arquivo(self) -> pd.DataFrame:
        arquivos_validos = self.__listar_arquivos_validos()
        
        if len(arquivos_validos) < 1:
            raise ValueError('Nenhum arquivo válido encontrado')
        
        lista_dataframes = []
        for arquivo in arquivos_validos:

            caminho_arquivo = os.path.join(self.pasta, arquivo)
            try:
                lista_dataframes.append(pd.read_csv(caminho_arquivo, sep=',', encoding='utf-8'))
            except Exception as e:
                print(f'Erro ao carregar o arquivo {arquivo}: {e}')
                continue
        
        if len(lista_dataframes) < 1:
            return pd.DataFrame()
        
        volume_concatenado = pd.concat(lista_dataframes, ignore_index=True)
        return volume_concatenado


