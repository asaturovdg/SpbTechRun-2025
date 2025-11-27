from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    DB_HOST: str = Field(..., env="DB_HOST")
    DB_PORT: str = Field(..., env="DB_PORT")
    DB_USER: str = Field(..., env="DB_USER")
    DB_PASSWORD: str = Field(..., env="DB_PASSWORD")
    DB_DB: str = Field(..., env="DB_DB")
    DB_ECHO: bool = Field(False, env="DB_ECHO")

    @property
    def database_url_async(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DB}"
        )
    
    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DB}"
        )

    @property
    def database_echo(self) -> bool:
        """
        Controls SQLAlchemy engine `echo` flag.

        Can be configured via the `DB_ECHO` environment variable.
        """
        return self.DB_ECHO

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
