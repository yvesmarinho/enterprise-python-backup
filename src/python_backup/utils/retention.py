"""
Retention policy utilities for backup management.

Implements retention logic for keeping/deleting backups based on age.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    """
    Retention policy configuration.
    
    Defines how many backups to keep for different time periods:
    - hourly: Keep backups for last N hours
    - daily: Keep daily backups for last N days
    - weekly: Keep weekly backups for last N weeks
    - monthly: Keep monthly backups for last N months
    """
    hourly: int = 0
    daily: int = 0
    weekly: int = 0
    monthly: int = 0


def should_keep_backup(backup_time: datetime, policy: RetentionPolicy, 
                       current_time: datetime) -> bool:
    """
    Determine if a backup should be kept based on retention policy.
    
    Args:
        backup_time: When the backup was created
        policy: Retention policy to apply
        current_time: Current time for comparison
        
    Returns:
        bool: True if backup should be kept, False otherwise
    """
    age = current_time - backup_time
    
    # Check hourly retention
    if policy.hourly > 0:
        if age <= timedelta(hours=policy.hourly):
            return True
    
    # Check daily retention
    if policy.daily > 0:
        if age <= timedelta(days=policy.daily):
            return True
    
    # Check weekly retention
    if policy.weekly > 0:
        if age <= timedelta(weeks=policy.weekly):
            return True
    
    # Check monthly retention (approximate as 30 days)
    if policy.monthly > 0:
        if age <= timedelta(days=policy.monthly * 30):
            return True
    
    return False


def apply_retention_policy(backups: List[Dict[str, Any]], 
                          policy: RetentionPolicy,
                          current_time: datetime) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Apply retention policy to list of backups.
    
    Args:
        backups: List of backup dictionaries with 'timestamp' key
        policy: Retention policy to apply
        current_time: Current time for comparison
        
    Returns:
        tuple: (backups_to_keep, backups_to_delete)
    """
    to_keep = []
    to_delete = []
    
    for backup in backups:
        if 'timestamp' not in backup:
            logger.warning(f"Backup missing timestamp: {backup}")
            continue
        
        backup_time = backup['timestamp']
        
        if should_keep_backup(backup_time, policy, current_time):
            to_keep.append(backup)
        else:
            to_delete.append(backup)
    
    logger.info(f"Retention policy: keeping {len(to_keep)}, deleting {len(to_delete)}")
    return to_keep, to_delete


def parse_retention_string(retention_str: str) -> RetentionPolicy:
    """
    Parse retention string to RetentionPolicy.
    
    Format: "7d,4w,12m" (7 days, 4 weeks, 12 months)
    Supported suffixes: h (hours), d (days), w (weeks), m (months)
    
    Args:
        retention_str: Retention string to parse
        
    Returns:
        RetentionPolicy: Parsed policy
        
    Examples:
        >>> parse_retention_string("24h,7d,4w,12m")
        RetentionPolicy(hourly=24, daily=7, weekly=4, monthly=12)
        
        >>> parse_retention_string("7d,4w")
        RetentionPolicy(hourly=0, daily=7, weekly=4, monthly=0)
    """
    policy = RetentionPolicy()
    
    try:
        parts = retention_str.split(',')
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Extract number and suffix
            value = int(part[:-1])
            suffix = part[-1].lower()
            
            if suffix == 'h':
                policy.hourly = value
            elif suffix == 'd':
                policy.daily = value
            elif suffix == 'w':
                policy.weekly = value
            elif suffix == 'm':
                policy.monthly = value
            else:
                logger.warning(f"Unknown retention suffix: {suffix}")
        
        logger.debug(f"Parsed retention policy: {policy}")
        return policy
        
    except Exception as e:
        logger.error(f"Error parsing retention string: {e}")
        return RetentionPolicy()
