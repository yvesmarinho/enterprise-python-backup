"""
Email notification system for VYA BackupDB.

Sends email notifications for backup success or failure.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Email configuration."""
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    use_ssl: bool = False
    use_tls: bool = False
    from_email: str = ""
    success_recipients: List[str] = None
    failure_recipients: List[str] = None
    test_mode: bool = False
    
    def __post_init__(self):
        if self.success_recipients is None:
            self.success_recipients = []
        if self.failure_recipients is None:
            self.failure_recipients = []


class EmailSender:
    """
    Email notification sender for backup operations.
    
    Sends formatted emails with backup results to appropriate recipients.
    """
    
    def __init__(self, config: EmailConfig):
        """
        Initialize email sender.
        
        Args:
            config: Email configuration
        """
        logger.debug(f"=== Função: __init__ (EmailSender) ===")
        logger.debug(f"==> PARAM: config TYPE: {type(config)}, CONTENT: {config}")
        
        self.config = config
        logger.debug(f"=== Término Função: __init__ (EmailSender) ===")
    
    def send_success_notification(
        self, 
        instance: str,
        databases: List[str],
        backup_info: Dict[str, Any]
    ) -> bool:
        """
        Send success notification email.
        
        Args:
            instance: Database instance identifier
            databases: List of backed up databases
            backup_info: Dictionary with backup statistics
            
        Returns:
            True if email sent successfully, False otherwise
        """
        logger.debug(f"=== Função: send_success_notification (EmailSender) ===")
        logger.debug(f"==> PARAM: instance TYPE: {type(instance)}, SIZE: {len(instance)} chars, CONTENT: {instance}")
        logger.debug(f"==> PARAM: databases TYPE: {type(databases)}, SIZE: {len(databases)} items")
        logger.debug(f"==> PARAM: backup_info TYPE: {type(backup_info)}, SIZE: {len(backup_info)} keys")
        
        if not self.config.enabled:
            logger.info("Email notifications disabled, skipping success notification")
            logger.debug(f"=== Término Função: send_success_notification (EmailSender) ===")
            return True
        
        try:
            subject = self._build_subject(True)
            body = self._build_success_body(instance, databases, backup_info)
            recipients = self.config.success_recipients
            
            result = self._send_email(recipients, subject, body)
            
            logger.debug(f"=== Término Função: send_success_notification (EmailSender) ===")
            return result
            
        except Exception as e:
            logger.error(f"Error sending success notification: {e}")
            logger.debug(f"=== Término Função: send_success_notification (EmailSender) COM ERRO ===")
            return False
    
    def send_failure_notification(
        self,
        instance: str,
        failed_databases: List[str],
        errors: Dict[str, str],
        log_file: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send failure notification email.
        
        Args:
            instance: Database instance identifier
            failed_databases: List of databases that failed to backup
            errors: Dictionary mapping database names to error messages
            log_file: Path to log file to attach (optional)
            additional_info: Additional information to include in email (optional)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        logger.debug(f"=== Função: send_failure_notification (EmailSender) ===")
        logger.debug(f"==> PARAM: instance TYPE: {type(instance)}, SIZE: {len(instance)} chars, CONTENT: {instance}")
        logger.debug(f"==> PARAM: failed_databases TYPE: {type(failed_databases)}, SIZE: {len(failed_databases)} items")
        logger.debug(f"==> PARAM: errors TYPE: {type(errors)}, SIZE: {len(errors)} keys")
        
        if not self.config.enabled:
            logger.info("Email notifications disabled, skipping failure notification")
            logger.debug(f"=== Término Função: send_failure_notification (EmailSender) ===")
            return True
        
        try:
            subject = self._build_subject(False)
            body = self._build_failure_body(instance, failed_databases, errors, additional_info)
            recipients = self.config.failure_recipients
            
            attachments = []
            if log_file and Path(log_file).exists():
                attachments.append(log_file)
            
            result = self._send_email(recipients, subject, body, attachments)
            
            logger.debug(f"=== Término Função: send_failure_notification (EmailSender) ===")
            return result
            
        except Exception as e:
            logger.error(f"Error sending failure notification: {e}")
            logger.debug(f"=== Término Função: send_failure_notification (EmailSender) COM ERRO ===")
            return False
    
    def _build_subject(self, success: bool) -> str:
        """Build email subject line."""
        status = "SUCESSO" if success else "FALHA"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        subject = f"VYA BackupDB - {status} - {timestamp}"
        
        # Add TESTE at the end if in test mode
        if self.config.test_mode:
            subject += " - TESTE"
        
        return subject
    
    def _build_success_body(
        self,
        instance: str,
        databases: List[str],
        backup_info: Dict[str, Any]
    ) -> str:
        """Build success email body."""
        total_size = backup_info.get('total_size_mb', 0)
        success_count = backup_info.get('success_count', len(databases))
        
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .info {{ background-color: #f1f1f1; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .database-list {{ list-style-type: none; padding: 0; }}
                .database-list li {{ padding: 5px; border-bottom: 1px solid #ddd; }}
                .footer {{ color: #666; font-size: 12px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>✅ Backup Realizado com Sucesso</h1>
            </div>
            <div class="content">
                <div class="info">
                    <p><strong>Instância:</strong> {instance}</p>
                    <p><strong>Data/Hora:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</p>
                    <p><strong>Bancos Processados:</strong> {success_count}</p>
                    <p><strong>Tamanho Total:</strong> {total_size:.2f} MB</p>
                </div>
                
                <h3>Bancos de Dados Backupeados:</h3>
                <ul class="database-list">
        """
        
        for db in databases:
            body += f"                    <li>✓ {db}</li>\n"
        
        body += """
                </ul>
                
                <div class="footer">
                    <p>Este é um email automático do sistema VYA BackupDB.</p>
                    <p>Para mais informações, consulte os logs em /var/log/enterprise/</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return body
    
    def _build_failure_body(
        self,
        instance: str,
        failed_databases: List[str],
        errors: Dict[str, str],
        additional_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build failure email body with detailed error information."""
        # Extract additional info
        total_attempted = additional_info.get('total_attempted', len(failed_databases)) if additional_info else len(failed_databases)
        log_file_path = additional_info.get('log_file', 'N/A') if additional_info else 'N/A'
        execution_time = additional_info.get('execution_time', 'N/A') if additional_info else 'N/A'
        
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #f44336; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .info {{ background-color: #f1f1f1; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .warning-box {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0; }}
                .error-list {{ list-style-type: none; padding: 0; }}
                .error-list li {{ padding: 10px; border-bottom: 1px solid #ddd; background-color: #ffebee; margin: 5px 0; border-radius: 3px; }}
                .error-db {{ font-weight: bold; color: #d32f2f; }}
                .error-msg {{ color: #666; font-size: 14px; margin-top: 5px; font-family: monospace; white-space: pre-wrap; }}
                .footer {{ color: #666; font-size: 12px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; }}
                .attachment-notice {{ background-color: #e3f2fd; padding: 10px; margin: 15px 0; border-left: 4px solid #2196F3; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>❌ Falha no Backup</h1>
            </div>
            <div class="content">
                <div class="info">
                    <p><strong>Instância:</strong> {instance}</p>
                    <p><strong>Data/Hora:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</p>
                    <p><strong>Bancos Tentados:</strong> {total_attempted}</p>
                    <p><strong>Bancos com Falha:</strong> {len(failed_databases)}</p>
                    <p><strong>Tempo de Execução:</strong> {execution_time}</p>
                    <p><strong>Arquivo de Log:</strong> {log_file_path}</p>
                </div>
                
                <div class="warning-box">
                    <strong>⚠️ ATENÇÃO:</strong> Falhas no backup podem resultar em perda de dados. 
                    Verificar e corrigir imediatamente!
                </div>
                
                <h3>Detalhes dos Erros:</h3>
                <ul class="error-list">
        """
        
        for db in failed_databases:
            error_msg = errors.get(db, "Erro desconhecido")
            body += f"""
                    <li>
                        <div class="error-db">✗ {db}</div>
                        <div class="error-msg">{error_msg}</div>
                    </li>
            """
        
        body += """
                </ul>
                
                <div class="attachment-notice">
                    <strong>📎 Anexo:</strong> O arquivo de log completo está anexado a este email para análise detalhada.
                </div>
                
                <div class="footer">
                    <p><strong>⚠️ Ação Requerida:</strong></p>
                    <ul>
                        <li>Verificar os detalhes dos erros acima</li>
                        <li>Analisar o arquivo de log anexado</li>
                        <li>Corrigir os problemas identificados</li>
                        <li>Re-executar o backup dos bancos com falha</li>
                    </ul>
                    <p>Logs também disponíveis em: /var/log/enterprise/</p>
                    <p>Este é um email automático do sistema VYA BackupDB.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return body
    
    def _send_email(self, recipients: List[str], subject: str, body: str, attachments: Optional[List[str]] = None) -> bool:
        """
        Send email using SMTP.
        
        Args:
            recipients: List of email addresses
            subject: Email subject
            body: Email body (HTML)
            attachments: List of file paths to attach (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        logger.debug(f"=== Função: _send_email (EmailSender) ===")
        logger.debug(f"==> PARAM: recipients TYPE: {type(recipients)}, SIZE: {len(recipients)} items")
        logger.debug(f"==> PARAM: subject TYPE: {type(subject)}, SIZE: {len(subject)} chars")
        logger.debug(f"==> PARAM: body TYPE: {type(body)}, SIZE: {len(body)} chars")
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config.from_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            # Attach HTML body
            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Attach files if provided
            if attachments:
                for file_path in attachments:
                    try:
                        path = Path(file_path)
                        if path.exists() and path.is_file():
                            with open(file_path, 'rb') as f:
                                part = MIMEBase('application', 'octet-stream')
                                part.set_payload(f.read())
                                encoders.encode_base64(part)
                                part.add_header(
                                    'Content-Disposition',
                                    f'attachment; filename="{path.name}"'
                                )
                                msg.attach(part)
                                logger.info(f"Attached file: {path.name}")
                        else:
                            logger.warning(f"Attachment file not found: {file_path}")
                    except Exception as e:
                        logger.error(f"Error attaching file {file_path}: {e}")
            
            # Connect and send
            logger.info(f"Connecting to SMTP server: {self.config.smtp_host}:{self.config.smtp_port}")
            
            # Use SMTP_SSL if use_ssl is enabled, otherwise use regular SMTP
            if self.config.use_ssl:
                import smtplib
                server = smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port, timeout=30)
                logger.debug("Using SMTP_SSL connection")
            else:
                server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=30)
                logger.debug("Using regular SMTP connection")
                
                if self.config.use_tls:
                    logger.debug("Starting TLS connection")
                    server.starttls()
            
            try:
                if self.config.smtp_user and self.config.smtp_password:
                    logger.debug("Authenticating with SMTP server")
                    server.login(self.config.smtp_user, self.config.smtp_password)
                
                logger.info(f"Sending email to: {recipients}")
                server.send_message(msg)
                
                logger.info(f"Email sent successfully to {len(recipients)} recipient(s)")
                logger.debug(f"=== Término Função: _send_email (EmailSender) ===")
                return True
            finally:
                server.quit()
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            logger.debug(f"=== Término Função: _send_email (EmailSender) COM ERRO ===")
            return False
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            logger.debug(f"=== Término Função: _send_email (EmailSender) COM ERRO ===")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            logger.debug(f"=== Término Função: _send_email (EmailSender) COM ERRO ===")
            return False
