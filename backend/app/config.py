from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://orbitwatch:orbitwatch@localhost:5432/orbitwatch"
    celestrak_groups: str = "stations,active"
    ingest_interval_hours: float = 2.0
    cors_origins: str = "http://localhost:5173"

    @property
    def groups(self) -> list[str]:
        return [g.strip() for g in self.celestrak_groups.split(",") if g.strip()]

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
