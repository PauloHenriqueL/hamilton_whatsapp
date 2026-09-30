import requests
import os

class Webmania:
    def __init__(self):

        self.__ambiente = 1
        
        self.__base_url = 'https://api.webmaniabr.com/2'
        
        api_token = os.getenv('WEBMANIA_API_TOKEN')
        if not api_token:
            raise ValueError("A variável de ambiente 'WEBMANIA_API_TOKEN' não foi definida no .env")

        self.__headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_token}'
        }

    def send_nfs(self, nfs_info):
        payload = {
            "ambiente": self.__ambiente,
            "rps": [nfs_info],
        }
        try:
            response = requests.post(f'{self.__base_url}/nfse/emissao', headers=self.__headers, json=payload, timeout=30)
            return response.json()
        except requests.exceptions.RequestException as e:
            return {'error': f'Erro de conexão: {e}'}

    def get_nfs(self, nfs_id):
        try:
            response = requests.get(f'{self.__base_url}/nfse/consulta/{nfs_id}', headers=self.__headers, timeout=30)
            return response.json()
        except requests.exceptions.RequestException as e:
            return {'error': f'Erro de conexão: {e}'}

    def cancelar_nfs(self, nfs_id, motivo):
        # No Padrão Nacional via Webmania, o UUID vai no corpo e o método é PUT
        payload = {
            'uuid': nfs_id,
            'motivo': motivo 
        }
        try:
            # CORREÇÃO: Método PUT e URL base (sem o ID no final)
            response = requests.put(
                f'{self.__base_url}/nfse/cancelar',
                headers=self.__headers,
                json=payload,
                timeout=30
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            return {'error': f'Erro de conexão: {e}'}

    def get_nfs_pdf_content(self, nfs_id):
        nfs_data = self.get_nfs(nfs_id=nfs_id)
        if nfs_data and nfs_data.get('status') == 'aprovado' and nfs_data.get('pdf_nfse'):
            pdf_url = nfs_data['pdf_nfse']
            try:
                pdf_response = requests.get(pdf_url)
                return pdf_response.content
            except requests.exceptions.RequestException:
                return None
        return None

    def get_nfs_xml_content(self, nfs_id):
        nfs_data = self.get_nfs(nfs_id=nfs_id)
        if nfs_data and nfs_data.get('status') == 'aprovado' and nfs_data.get('xml'):
            xml_url = nfs_data['xml']
            try:
                xml_response = requests.get(xml_url)
                return xml_response.content
            except requests.exceptions.RequestException:
                return None
        return None