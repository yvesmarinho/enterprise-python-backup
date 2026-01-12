"""
SQLAlchemy engine factory for database connections.

Creates and configures SQLAlchemy engines with proper connection
pooling, timeouts, and SSL settings.
"""

from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from vya_backupbd.config.models import DatabaseConfig


def get_connection_string(config: DatabaseConfig) -> str:
    """
    Generate database connection string from configuration.
    
    Args:
        config: Database configuration
        
    Returns:
        SQLAlchemy connection string
        
    Raises:
        ValueError: If database type is not supported
    """
    # URL encode password to handle special characters
    password = quote_plus(config.password)
    username = quote_plus(config.username)
    
    if config.type == "mysql":
        # MySQL connection string with pymysql driver
        conn_str = (
            f"mysql+pymysql://{username}:{password}@"
            f"{config.host}:{config.port}/{config.database}"
        )
        
        # Add SSL parameter if enabled
        if config.ssl:
            conn_str += "?ssl=true"
            
        return conn_str
        
    elif config.type == "postgresql":
        # PostgreSQL connection string with psycopg driver
        conn_str = (
            f"postgresql+psycopg://{username}:{password}@"
            f"{config.host}:{config.port}/{config.database}"
        )
        
        # Add SSL mode if enabled
        if config.ssl:
            conn_str += "?sslmode=require"
            
        return conn_str
        
    else:
        raise ValueError(f"Unsupported database type: {config.type}")


def create_db_engine(
    config: DatabaseConfig,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
    echo: bool = False
) -> Engine:
    """
    Create SQLAlchemy engine with connection pooling.
    
    Args:
        config: Database configuration
        pool_size: Size of the connection pool (default: 5)
        max_overflow: Maximum overflow connections (default: 10)
        pool_timeout: Timeout for getting connection from pool in seconds (default: 30)
        pool_recycle: Recycle connections after N seconds (default: 3600)
        echo: Enable SQL query logging (default: False)
        
    Returns:
        Configured SQLAlchemy engine
        
    Example:
        >>> config = DatabaseConfig(...)
        >>> engine = create_db_engine(config)
        >>> with engine.connect() as conn:
        ...     result = conn.execute("SELECT 1")
    """
    connection_string = get_connection_string(config)
    
    engine = create_engine(
        connection_string,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        echo=echo,
        pool_pre_ping=True,  # Verify connections before using
    )
    
    return engine
