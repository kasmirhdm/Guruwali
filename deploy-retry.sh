#!/bin/bash
# Auto-deploy GuruWali frontend saat SSH pulih
LOG=~/workspace/guruwali/deploy-retry.log
if ssh -F /home/hatch/.ssh/config -o ConnectTimeout=10 vps-tailscale "echo OK" 2>/dev/null | grep -q "OK"; then
    echo "[$(date)] SSH OK, deploying..." >> $LOG
    rsync -avz --exclude 'auth.db' -e "ssh -F /home/hatch/.ssh/config" ~/workspace/guruwali/frontend/ vps-tailscale:/opt/guruwali/frontend/ >> $LOG 2>&1
    ssh -F /home/hatch/.ssh/config vps-tailscale "chmod -R 755 /opt/guruwali/frontend" >> $LOG 2>&1
    echo "[$(date)] DEPLOYED" >> $LOG
    # Hapus cron setelah berhasil
    crontab -l 2>/dev/null | grep -v "deploy-retry.sh" | crontab -
    echo "[$(date)] Cron dihapus, selesai!" >> $LOG
else
    echo "[$(date)] SSH masih down" >> $LOG
fi
