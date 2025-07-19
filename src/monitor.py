#!/usr/bin/env python3
"""
PCBot Monitoring Script
Monitors logs, performance, and system health
"""

import os
import sys
import time
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import psutil
import threading
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitoring.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class PCBotMonitor:
    """PCBot monitoring system"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(tempfile.gettempdir(), 'pcbot_security.db')
        self.running = False
        self.monitor_thread = None
        self.stats = {
            'uptime': 0,
            'total_users': 0,
            'active_sessions': 0,
            'total_files_processed': 0,
            'total_bytes_transferred': 0,
            'security_events_24h': 0,
            'errors_24h': 0,
            'last_check': None
        }
        
    def start_monitoring(self):
        """Start the monitoring service"""
        logger.info("Starting PCBot monitoring service...")
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Monitoring service started")
        
    def stop_monitoring(self):
        """Stop the monitoring service"""
        logger.info("Stopping monitoring service...")
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Monitoring service stopped")
        
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._collect_stats()
                self._check_health()
                self._log_stats()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)  # Wait before retry
                
    def _collect_stats(self):
        """Collect system and application statistics"""
        try:
            # Update last check time
            self.stats['last_check'] = datetime.now().isoformat()
            
            # System statistics
            system_stats = self._get_system_stats()
            self.stats.update(system_stats)
            
            # Database statistics
            if os.path.exists(self.db_path):
                db_stats = self._get_database_stats()
                self.stats.update(db_stats)
                
        except Exception as e:
            logger.error(f"Error collecting stats: {e}")
            
    def _get_system_stats(self) -> Dict[str, Any]:
        """Get system performance statistics"""
        try:
            # CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network I/O
            net_io = psutil.net_io_counters()
            
            # Process information
            process_count = len(psutil.pids())
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available': memory.available,
                'disk_percent': disk.percent,
                'disk_free': disk.free,
                'network_bytes_sent': net_io.bytes_sent,
                'network_bytes_recv': net_io.bytes_recv,
                'process_count': process_count
            }
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}
            
    def _get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # User statistics
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]
                
                # Security events in last 24 hours
                yesterday = (datetime.now() - timedelta(hours=24)).isoformat()
                cursor.execute("""
                    SELECT COUNT(*) FROM security_events 
                    WHERE timestamp > ?
                """, (yesterday,))
                security_events_24h = cursor.fetchone()[0]
                
                # Error events in last 24 hours
                cursor.execute("""
                    SELECT COUNT(*) FROM security_events 
                    WHERE timestamp > ? AND success = 0
                """, (yesterday,))
                errors_24h = cursor.fetchone()[0]
                
                # File quota statistics
                cursor.execute("SELECT SUM(used_quota), SUM(file_count) FROM file_quotas")
                quota_result = cursor.fetchone()
                total_bytes_used = quota_result[0] or 0
                total_files = quota_result[1] or 0
                
                # Temporary files
                cursor.execute("SELECT COUNT(*), SUM(file_size) FROM temp_files")
                temp_result = cursor.fetchone()
                temp_files_count = temp_result[0] or 0
                temp_files_size = temp_result[1] or 0
                
                return {
                    'total_users': total_users,
                    'security_events_24h': security_events_24h,
                    'errors_24h': errors_24h,
                    'total_bytes_used': total_bytes_used,
                    'total_files': total_files,
                    'temp_files_count': temp_files_count,
                    'temp_files_size': temp_files_size
                }
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
            
    def _check_health(self):
        """Check system health and alert on issues"""
        try:
            # Check disk space
            if self.stats.get('disk_percent', 0) > 90:
                logger.warning(f"Disk space critical: {self.stats['disk_percent']}% used")
                
            # Check memory usage
            if self.stats.get('memory_percent', 0) > 85:
                logger.warning(f"Memory usage high: {self.stats['memory_percent']}% used")
                
            # Check CPU usage
            if self.stats.get('cpu_percent', 0) > 80:
                logger.warning(f"CPU usage high: {self.stats['cpu_percent']}%")
                
            # Check error rate
            if self.stats.get('errors_24h', 0) > 100:
                logger.warning(f"High error rate: {self.stats['errors_24h']} errors in 24h")
                
            # Check temporary files
            if self.stats.get('temp_files_count', 0) > 1000:
                logger.warning(f"Many temporary files: {self.stats['temp_files_count']} files")
                
        except Exception as e:
            logger.error(f"Error checking health: {e}")
            
    def _log_stats(self):
        """Log current statistics"""
        try:
            stats_summary = {
                'timestamp': self.stats['last_check'],
                'system': {
                    'cpu_percent': self.stats.get('cpu_percent', 'N/A'),
                    'memory_percent': self.stats.get('memory_percent', 'N/A'),
                    'disk_percent': self.stats.get('disk_percent', 'N/A')
                },
                'application': {
                    'total_users': self.stats.get('total_users', 0),
                    'total_files': self.stats.get('total_files', 0),
                    'security_events_24h': self.stats.get('security_events_24h', 0),
                    'errors_24h': self.stats.get('errors_24h', 0)
                }
            }
            
            logger.info(f"System Stats: {json.dumps(stats_summary, indent=2)}")
            
        except Exception as e:
            logger.error(f"Error logging stats: {e}")
            
    def get_status_report(self) -> Dict[str, Any]:
        """Generate a comprehensive status report"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'monitoring_status': 'running' if self.running else 'stopped',
                'system_health': self._get_health_status(),
                'statistics': self.stats.copy(),
                'recommendations': self._get_recommendations()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating status report: {e}")
            return {'error': str(e)}
            
    def _get_health_status(self) -> str:
        """Determine overall health status"""
        try:
            issues = []
            
            if self.stats.get('disk_percent', 0) > 90:
                issues.append('disk_space_critical')
            elif self.stats.get('disk_percent', 0) > 80:
                issues.append('disk_space_warning')
                
            if self.stats.get('memory_percent', 0) > 85:
                issues.append('memory_high')
                
            if self.stats.get('cpu_percent', 0) > 80:
                issues.append('cpu_high')
                
            if self.stats.get('errors_24h', 0) > 100:
                issues.append('high_error_rate')
                
            if not issues:
                return 'healthy'
            elif any(issue.endswith('_critical') for issue in issues):
                return 'critical'
            else:
                return 'warning'
                
        except Exception as e:
            logger.error(f"Error determining health status: {e}")
            return 'unknown'
            
    def _get_recommendations(self) -> List[str]:
        """Get system recommendations"""
        recommendations = []
        
        try:
            if self.stats.get('disk_percent', 0) > 80:
                recommendations.append("Consider cleaning up temporary files or expanding disk space")
                
            if self.stats.get('memory_percent', 0) > 80:
                recommendations.append("Monitor memory usage and consider increasing RAM")
                
            if self.stats.get('temp_files_count', 0) > 500:
                recommendations.append("Run cleanup to remove temporary files")
                
            if self.stats.get('errors_24h', 0) > 50:
                recommendations.append("Review error logs and address recurring issues")
                
            if self.stats.get('total_users', 0) > 100:
                recommendations.append("Consider implementing user management policies")
                
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            
        return recommendations
        
    def export_stats(self, filename: str = None) -> str:
        """Export statistics to JSON file"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"pcbot_stats_{timestamp}.json"
                
            report = self.get_status_report()
            
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
                
            logger.info(f"Statistics exported to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error exporting stats: {e}")
            return None


def main():
    """Main monitoring function"""
    monitor = PCBotMonitor()
    
    try:
        print("🔍 PCBot Monitor Starting...")
        print("=" * 50)
        
        # Start monitoring
        monitor.start_monitoring()
        
        # Interactive commands
        while True:
            try:
                print("\n📊 PCBot Monitor Commands:")
                print("1. Show current stats")
                print("2. Export stats to file")
                print("3. Show recommendations")
                print("4. Quit")
                
                choice = input("\nEnter choice (1-4): ").strip()
                
                if choice == '1':
                    report = monitor.get_status_report()
                    print("\n📈 Current Status:")
                    print(f"Health: {report['system_health']}")
                    print(f"Users: {report['statistics'].get('total_users', 0)}")
                    print(f"Files: {report['statistics'].get('total_files', 0)}")
                    print(f"CPU: {report['statistics'].get('cpu_percent', 'N/A')}%")
                    print(f"Memory: {report['statistics'].get('memory_percent', 'N/A')}%")
                    print(f"Disk: {report['statistics'].get('disk_percent', 'N/A')}%")
                    
                elif choice == '2':
                    filename = monitor.export_stats()
                    if filename:
                        print(f"✅ Stats exported to {filename}")
                    else:
                        print("❌ Failed to export stats")
                        
                elif choice == '3':
                    report = monitor.get_status_report()
                    recommendations = report.get('recommendations', [])
                    if recommendations:
                        print("\n💡 Recommendations:")
                        for i, rec in enumerate(recommendations, 1):
                            print(f"{i}. {rec}")
                    else:
                        print("✅ No recommendations - system is healthy")
                        
                elif choice == '4':
                    break
                    
                else:
                    print("❌ Invalid choice")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user")
    except Exception as e:
        print(f"❌ Critical error: {e}")
    finally:
        monitor.stop_monitoring()
        print("🔍 PCBot Monitor Stopped")


if __name__ == "__main__":
    main()
