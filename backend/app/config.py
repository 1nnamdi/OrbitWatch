from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://orbitwatch:orbitwatch@localhost:5432/orbitwatch"
    celestrak_groups: str = "stations,active"
    ingest_interval_hours: float = 2.0
    launches_interval_hours: float = 1.0  # LL2 free tier: 15 req/hour
    spacetrack_user: str = ""
    spacetrack_password: str = ""
    spacetrack_interval_hours: float = 12.0  # satcat guidance: query at most daily
    cors_origins: str = "http://localhost:5173"

    @property
    def groups(self) -> list[str]:
        return [g.strip() for g in self.celestrak_groups.split(",") if g.strip()]

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
