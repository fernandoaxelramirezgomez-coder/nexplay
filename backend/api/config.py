"""Configuración de Nia, leída del entorno o de un .env que no se versiona.

La clave de OpenAI nunca vive en el repo: en local va en .env (ignorado por git) y en
el despliegue se carga como variable de entorno o secreto del proveedor. Sin clave o
sin modelo, Nia responde en modo demostración con reglas sobre los datos reales.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# El .env vive en la raíz del repo, junto a .env.example, aunque la API corra desde backend/.
_ENV = Path(__file__).resolve().parents[2] / ".env"


class ConfiguracionNia(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV, env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    nexplay_modelo_nia: str = ""
    nexplay_nia_max_tokens: int = 400
    # Con un modelo de razonamiento los tokens de pensar cuentan en el tope de salida: con
    # 400 la respuesta podía salir vacía. Con esto en true se piden 1,200 y esfuerzo "low";
    # en false (un modelo de chat) se pide esfuerzo "none" y temperatura baja.
    nexplay_nia_razonamiento: bool = False
    nexplay_nia_timeout: float = 20.0
    nexplay_nia_por_minuto: int = 10
    # Por IP, aparte: un salón con el mismo Wi-Fi comparte la IP. Sin valor, VECES_POR_IP el de una persona.
    nexplay_nia_por_minuto_ip: int | None = None
    # De todos juntos, solo con modelo de pago: acota el gasto aunque alguien cambie de id y de IP.
    nexplay_nia_por_minuto_global: int = 120

    @property
    def hay_openai(self) -> bool:
        return bool(self.openai_api_key.strip() and self.nexplay_modelo_nia.strip())


# Cuántas personas caben en el tope de una IP compartida.
VECES_POR_IP = 6


configuracion = ConfiguracionNia()
