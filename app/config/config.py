from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    DB_HOST: str = Field(..., env="DB_HOST")
    DB_PORT: str = Field(..., env="DB_PORT")
    DB_USER: str = Field(..., env="DB_USER")
    DB_PASSWORD: str = Field(..., env="DB_PASSWORD")
    DB_DB: str = Field(..., env="DB_DB")
    DB_ECHO: bool = Field(False, env="DB_ECHO")

    OLLAMA_HOST: str = Field(..., env="OLLAMA_HOST")
    OLLAMA_PORT: str = Field(..., env="OLLAMA_PORT")
    
    # Demo mode for presentation - amplifies learning effects
    DEMO_MODE: bool = Field(True, env="DEMO_MODE")
    
    # Thompson Sampling parameters (can be overridden via env)
    TS_INIT_STRENGTH: float = Field(4.0, env="TS_INIT_STRENGTH")       # How much similarity affects initial prior
    TS_UPDATE_STRENGTH_DEMO: float = Field(10.0, env="TS_UPDATE_STRENGTH_DEMO")  # Update strength in demo mode (visible effect)
    TS_UPDATE_STRENGTH_NORMAL: float = Field(1.0, env="TS_UPDATE_STRENGTH_NORMAL")  # Update strength in normal mode
    TS_MAX_TOTAL: float = Field(100.0, env="TS_MAX_TOTAL")             # Cap on alpha + beta
    
    # Scoring weight parameters
    TS_BASE_WEIGHT_DEMO: float = Field(0.8, env="TS_BASE_WEIGHT_DEMO")     # Base score weight in DEMO mode 
    TS_WEIGHT_HALFLIFE: float = Field(10.0, env="TS_WEIGHT_HALFLIFE")      # Feedback count for gamma=0.5 (normal mode)
    
    # MMR (Maximal Marginal Relevance) parameters for diversity
    MMR_ENABLED: bool = Field(True, env="MMR_ENABLED")                 # Enable MMR reranking
    MMR_RECALL_SIZE: int = Field(60, env="MMR_RECALL_SIZE")           # Number of candidates to retrieve before MMR
    MMR_RETURN_SIZE: int = Field(20, env="MMR_RETURN_SIZE")           # Number of items to return after MMR
    MMR_PURE_TOP_K: int = Field(3, env="MMR_PURE_TOP_K")              # Top K items exempt from MMR
    MMR_WINDOW_SIZE: int = Field(5, env="MMR_WINDOW_SIZE")            # Sliding window size for diversity check
    MMR_LAMBDA: float = Field(0.7, env="MMR_LAMBDA")                  # Relevance weight (1-λ = diversity weight)
    MMR_MIN_SCORE: float = Field(0.2, env="MMR_MIN_SCORE")            # Minimum relevance threshold
    
    @property
    def ts_update_strength(self) -> float:
        """Get update strength based on DEMO_MODE"""
        return self.TS_UPDATE_STRENGTH_DEMO if self.DEMO_MODE else self.TS_UPDATE_STRENGTH_NORMAL

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
    def ollama_url(self) -> str:
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"

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
