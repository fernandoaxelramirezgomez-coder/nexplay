"""Configuración de Nia, leída del entorno o de un .env que no se versiona.

La clave de OpenAI nunca vive en el repo: en local va en .env (ignorado por git) y en
el despliegue se carga como variable de entorno o secreto del proveedor. Sin clave o
sin modelo, Nia responde en modo demostración con reglas sobre los datos reales.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfiguracionNia(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    nexplay_modelo_nia: str = ""
    nexplay_nia_max_tokens: int = 400
    nexplay_nia_timeout: float = 20.0
    nexplay_nia_por_minuto: int = 10

    @property
    def hay_openai(self) -> bool:
        return bool(self.openai_api_key.strip() and self.nexplay_modelo_nia.strip())


configuracion = ConfiguracionNia()
