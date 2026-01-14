#!/usr/bin/env python3
"""
Test script to verify email failure notification with log attachment.
This simulates a backup failure and sends an email with detailed information.
"""

import sys
from pathlib import Path
import time
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from vya_backupbd.utils.email_sender import EmailSender, EmailConfig
from vya_backupbd.utils.logging_config import setup_logging

def main():
    """Test failure notification email."""
    
    print("=== Email Failure Notification Test ===\n")
    
    # Setup logging
    log_file = setup_logging(
        console_level="INFO",
        file_level="DEBUG",
        log_dir="/var/log/enterprise",
        app_name="vya_backupdb_test"
    )
    print(f"Log file: {log_file}\n")
    
    # Create email config
    email_config = EmailConfig(
        enabled=True,
        smtp_host="email-ssl.com.br",
        smtp_port=465,
        smtp_user="no-reply@vya.digital",
        smtp_password="4uC#9-UK69oTop=U+h2D",
        use_ssl=True,
        use_tls=False,
        from_email="no-reply@vya.digital",
        success_recipients=["yves.marinho@vya.digital"],
        failure_recipients=["yves.marinho@vya.digital"],
        test_mode=True
    )
    
    # Create email sender
    sender = EmailSender(email_config)
    
    # Simulate backup failure data
    instance = "mysql://154.53.36.3:3306"
    failed_databases = ["db_test1", "db_test2", "db_prod"]
    errors = {
        "db_test1": "Connection timeout: Could not connect to database server after 30 seconds",
        "db_test2": "Authentication failed: Invalid password for user 'backup_user'",
        "db_prod": "Disk full: No space left on device '/backup/mysql/'\nFailed to write dump file"
    }
    
    # Additional info
    execution_time = 245  # seconds
    execution_time_str = f"{int(execution_time // 60)}m {int(execution_time % 60)}s"
    
    additional_info = {
        'total_attempted': 5,  # 2 succeeded, 3 failed
        'log_file': log_file,
        'execution_time': execution_time_str
    }
    
    print("Sending failure notification email...")
    print(f"  Instance: {instance}")
    print(f"  Failed databases: {len(failed_databases)}")
    print(f"  Total attempted: {additional_info['total_attempted']}")
    print(f"  Execution time: {execution_time_str}")
    print(f"  Log file to attach: {log_file}\n")
    
    # Send email
    result = sender.send_failure_notification(
        instance=instance,
        failed_databases=failed_databases,
        errors=errors,
        log_file=log_file,
        additional_info=additional_info
    )
    
    if result:
        print("✅ Email sent successfully!")
        print("\nCheck your inbox for:")
        print("  - Detailed error information in HTML body")
        print("  - Warning box about backup failures")
        print("  - Execution statistics")
        print(f"  - Attached log file: {Path(log_file).name}")
    else:
        print("❌ Failed to send email")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
