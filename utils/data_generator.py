"""
Module: Simple CSV Generator
Purpose: Generate realistic network CSV data every 2 minutes
Dependencies: pandas, random, threading, config
"""

import pandas as pd
import random
import threading
import time
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DataGenerator:
    """Simple CSV data generator for network simulation"""

    def __init__(self, interval=120, data_dir=None, max_files=100, network_devices=None, vlans=None):
        self.interval = interval  # seconds
        self.data_dir = Path(data_dir) if data_dir else Path('data/network_data')
        self.max_files = max_files
        self.network_devices = network_devices or {}
        self.vlans = vlans or {}
        self.running = False
        self.thread = None
        self.callback = None

        # Create data directory
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Network IPs from config
        self.device_ips = self._extract_device_ips()
        self.vlan_ips = self._extract_vlan_ips()

    def _extract_device_ips(self):
        """Extract all device IPs from network config"""
        ips = []
        for device_config in self.network_devices.values():
            ips.append(device_config.get('management_ip'))
            for interface_ip in device_config.get('interfaces', {}).values():
                ips.append(interface_ip)
        return [ip for ip in ips if ip]

    def _extract_vlan_ips(self):
        """Extract VLAN device IPs"""
        ips = []
        for vlan_config in self.vlans.values():
            ips.extend(vlan_config.get('devices', []))
        return ips

    def start(self):
        """Start data generation"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"Data generator started (interval: {self.interval}s)")

    def stop(self):
        """Stop data generation"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Data generator stopped")

    def is_running(self):
        """Check if generator is running"""
        return self.running

    def set_callback(self, callback):
        """Set callback for new data notifications"""
        self.callback = callback

    def _run(self):
        """Main generation loop"""
        while self.running:
            try:
                self._generate_csv()
                self._cleanup_old_files()
            except Exception as e:
                logger.error(f"Error generating data: {str(e)}")

            # Wait for next interval
            time.sleep(self.interval)

    def _generate_csv(self):
        """Generate single CSV file with network data"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"network_data_{timestamp}.csv"
        filepath = self.data_dir / filename

        # Generate 50-200 rows of data
        num_rows = random.randint(50, 200)
        data = []

        for _ in range(num_rows):
            row = self._generate_network_row()
            data.append(row)

        # Create DataFrame
        df = pd.DataFrame(data)

        # Save to CSV
        df.to_csv(filepath, index=False)

        logger.info(f"Generated {filename} with {num_rows} rows")

        # Notify callback
        if self.callback:
            self.callback({
                'filename': filename,
                'filepath': str(filepath),
                'row_count': num_rows
            })

    def _generate_network_row(self):
        """Generate single network flow row"""
        # Random source and destination IPs
        all_ips = self.device_ips + self.vlan_ips
        if len(all_ips) < 2:
            # Fallback IPs if config not available
            all_ips = ['192.168.1.1', '192.168.1.2', '192.168.10.1', '192.168.20.1']

        src_ip = random.choice(all_ips)
        dst_ip = random.choice([ip for ip in all_ips if ip != src_ip])

        # Basic network features (35 features as per config)
        base_packets = random.randint(1, 1000)
        base_bytes = base_packets * random.randint(64, 1500)
        flow_duration = random.randint(1000, 300000000)  # microseconds

        return {
            # Network metadata
            'Timestamp': datetime.now().isoformat(),
            'Src IP': src_ip,
            'Dst IP': dst_ip,
            'Src Port': random.randint(1024, 65535),
            'Dst Port': random.choice([80, 443, 22, 25, 53, 21, 23, 993, 995]),

            # Flow features (35 required features)
            'Flow Duration': flow_duration,
            'Total Fwd Packets': base_packets,
            'Total Backward Packets': random.randint(1, base_packets),
            'Total Length of Fwd Packets': base_bytes,
            'Total Length of Bwd Packets': random.randint(64, base_bytes),
            'Fwd Packet Length Max': random.randint(64, 1500),
            'Fwd Packet Length Mean': random.randint(64, 800),
            'Fwd Packet Length Std': random.uniform(0, 100),
            'Bwd Packet Length Max': random.randint(64, 1500),
            'Bwd Packet Length Mean': random.randint(64, 800),
            'Bwd Packet Length Std': random.uniform(0, 100),
            'Flow Bytes/s': random.uniform(100, 1000000),
            'Flow Packets/s': random.uniform(1, 1000),
            'Flow IAT Mean': random.uniform(0, 10000),
            'Flow IAT Std': random.uniform(0, 5000),
            'Flow IAT Max': random.uniform(0, 50000),
            'Flow IAT Min': random.uniform(0, 1000),
            'Fwd IAT Total': random.uniform(0, 100000),
            'Fwd Header Length': random.randint(20, 100),
            'Bwd Header Length': random.randint(20, 100),
            'Min Packet Length': 64,
            'Max Packet Length': random.randint(64, 1500),
            'Packet Length Mean': random.randint(64, 800),
            'Packet Length Std': random.uniform(0, 200),
            'Packet Length Variance': random.uniform(0, 40000),
            'ACK Flag Count': random.randint(0, base_packets),
            'Down/Up Ratio': random.uniform(0, 10),
            'Average Packet Size': random.randint(64, 800),
            'Avg Bwd Segment Size': random.randint(0, 800),
            'Subflow Fwd Bytes': random.randint(0, base_bytes),
            'Init_Win_bytes_forward': random.randint(0, 65535),
            'Init_Win_bytes_backward': random.randint(0, 65535),
            'Idle Mean': random.uniform(0, 10000),
            'Idle Max': random.uniform(0, 50000),
            'Idle Min': random.uniform(0, 1000)
        }

    def _cleanup_old_files(self):
        """Remove old CSV files to maintain max_files limit"""
        try:
            csv_files = list(self.data_dir.glob('network_data_*.csv'))
            csv_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Remove excess files
            if len(csv_files) > self.max_files:
                for old_file in csv_files[self.max_files:]:
                    old_file.unlink()
                    logger.debug(f"Removed old file: {old_file.name}")

        except Exception as e:
            logger.error(f"Error cleaning up files: {str(e)}")

    def generate_now(self):
        """Generate CSV immediately (for testing)"""
        if not self.running:
            self._generate_csv()

    def get_latest_file(self):
        """Get path to latest generated CSV file"""
        try:
            csv_files = list(self.data_dir.glob('network_data_*.csv'))
            if csv_files:
                latest = max(csv_files, key=lambda x: x.stat().st_mtime)
                return latest
            return None
        except Exception as e:
            logger.error(f"Error getting latest file: {str(e)}")
            return None