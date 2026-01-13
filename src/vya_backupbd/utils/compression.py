"""
Compression utilities for backup files.

Supports zip, gzip and bzip2 compression/decompression.
"""

import gzip
import bz2
import zipfile
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def compress_file(source_file: str | Path, dest_file: str | Path, 
                 method: Optional[str] = None) -> bool:
    """
    Compress a file using specified method.
    
    Args:
        source_file: Source file path
        dest_file: Destination compressed file path
        method: Compression method ('zip', 'gzip' or 'bzip2'). If None, auto-detect from extension.
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.debug(f"=== Função: compress_file ===")
    logger.debug(f"==> PARAM: source_file TYPE: {type(source_file)}, SIZE: {len(str(source_file))} chars, CONTENT: {source_file}")
    logger.debug(f"==> PARAM: dest_file TYPE: {type(dest_file)}, SIZE: {len(str(dest_file))} chars, CONTENT: {dest_file}")
    logger.debug(f"==> PARAM: method TYPE: {type(method)}, CONTENT: {method}")
    
    try:
        source = Path(source_file)
        dest = Path(dest_file)
        
        if not source.exists():
            logger.error(f"Source file not found: {source}")
            return False
        
        # Auto-detect compression method from extension if not provided
        if method is None:
            if dest.suffix == '.gz':
                method = 'gzip'
            elif dest.suffix == '.bz2':
                method = 'bzip2'
            elif dest.suffix == '.zip':
                method = 'zip'
            else:
                method = 'gzip'  # Default to gzip
        
        # Compress based on method
        if method == 'zip':
            with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(source, arcname=source.name)
        elif method == 'gzip':
            with open(source, 'rb') as f_in:
                with gzip.open(dest, 'wb', compresslevel=6) as f_out:
                    f_out.writelines(f_in)
        elif method == 'bzip2':
            with open(source, 'rb') as f_in:
                with bz2.open(dest, 'wb', compresslevel=9) as f_out:
                    f_out.writelines(f_in)
        else:
            logger.error(f"Unknown compression method: {method}")
            logger.debug(f"=== Término Função: compress_file COM ERRO ===")
            return False
        
        logger.info(f"Compressed {source} to {dest} using {method}")
        logger.debug(f"=== Término Função: compress_file ===")
        return True
        
    except Exception as e:
        logger.error(f"Error compressing file: {e}")
        logger.debug(f"=== Término Função: compress_file COM ERRO ===")
        return False


def decompress_file(source_file: str | Path, dest_file: str | Path, 
                   method: Optional[str] = None) -> bool:
    """
    Decompress a file using specified method.
    
    Args:
        source_file: Source compressed file path
        dest_file: Destination decompressed file path
        method: Compression method ('gzip' or 'bzip2'). If None, auto-detect from extension.
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.debug(f"=== Função: decompress_file ===")
    logger.debug(f"==> PARAM: source_file TYPE: {type(source_file)}, SIZE: {len(str(source_file))} chars, CONTENT: {source_file}")
    logger.debug(f"==> PARAM: dest_file TYPE: {type(dest_file)}, SIZE: {len(str(dest_file))} chars, CONTENT: {dest_file}")
    logger.debug(f"==> PARAM: method TYPE: {type(method)}, CONTENT: {method}")
    
    try:
        source = Path(source_file)
        dest = Path(dest_file)
        
        if not source.exists():
            logger.error(f"Source file not found: {source}")
            return False
        
        # Auto-detect compression method from extension if not provided
        if method is None:
            if source.suffix == '.gz':
                method = 'gzip'
            elif source.suffix == '.bz2':
                method = 'bzip2'
            else:
                method = 'gzip'  # Default to gzip
        
        # Decompress based on method
        if method == 'gzip':
            with gzip.open(source, 'rb') as f_in:
                with open(dest, 'wb') as f_out:
                    f_out.writelines(f_in)
        elif method == 'bzip2':
            with bz2.open(source, 'rb') as f_in:
                with open(dest, 'wb') as f_out:
                    f_out.writelines(f_in)
        else:
            logger.error(f"Unknown compression method: {method}")
            logger.debug(f"=== Término Função: decompress_file COM ERRO ===")
            return False
        
        logger.info(f"Decompressed {source} to {dest} using {method}")
        logger.debug(f"=== Término Função: decompress_file ===")
        return True
        
    except Exception as e:
        logger.error(f"Error decompressing file: {e}")
        logger.debug(f"=== Término Função: decompress_file COM ERRO ===")
        return False


def get_compression_ratio(original_file: str | Path, 
                         compressed_file: str | Path) -> Optional[float]:
    """
    Calculate compression ratio.
    
    Args:
        original_file: Original file path
        compressed_file: Compressed file path
        
    Returns:
        float: Compression ratio (original_size / compressed_size), or None on error
    """
    logger.debug(f"=== Função: get_compression_ratio ===")
    logger.debug(f"==> PARAM: original_file TYPE: {type(original_file)}, SIZE: {len(str(original_file))} chars, CONTENT: {original_file}")
    logger.debug(f"==> PARAM: compressed_file TYPE: {type(compressed_file)}, SIZE: {len(str(compressed_file))} chars, CONTENT: {compressed_file}")
    
    try:
        original = Path(original_file)
        compressed = Path(compressed_file)
        
        if not original.exists() or not compressed.exists():
            logger.error("One or both files not found")
            return None
        
        original_size = original.stat().st_size
        compressed_size = compressed.stat().st_size
        
        if compressed_size == 0:
            return None
        
        ratio = original_size / compressed_size
        logger.debug(f"Compression ratio: {ratio:.2f}x")
        logger.debug(f"=== Término Função: get_compression_ratio ===")
        return ratio
        
    except Exception as e:
        logger.error(f"Error calculating compression ratio: {e}")
        logger.debug(f"=== Término Função: get_compression_ratio COM ERRO ===")
        return None
